
#!/usr/bin/env python3
"""Contributor checker script used by the workflow and by local tests.

This is a compact, dependency-light implementation that:
- collects contributors with `git log --use-mailmap` (PR range or all)
- parses `CITATION.cff` and `codemeta.json`
- normalizes names and compares
- posts a PR comment when credentials are present (requires `requests`)
"""

import os
import sys
import subprocess
import yaml
import json
import re
from pathlib import Path
from typing import Set

try:
	import requests
except Exception:
	requests = None


class ContributorChecker:
	def __init__(self) -> None:
		self.github_token = os.environ.get('GITHUB_TOKEN')
		self.github_repo = os.environ.get('GITHUB_REPOSITORY')
		self.pr_number = os.environ.get('PR_NUMBER')
		self.pr_base_sha = os.environ.get('PR_BASE_SHA')
		self.pr_head_sha = os.environ.get('PR_HEAD_SHA')
		self.repo_root = Path('.')
		self.config = self._load_config()

	def _load_config(self):
		cfg = self.repo_root / '.github' / 'contrib-metadata-check.yml'
		default = {
			'mode': 'warn',
			'ignore_emails': ['dependabot[bot]@users.noreply.github.com'],
			'ignore_logins': ['dependabot[bot]']
		}
		if cfg.exists():
			try:
				with open(cfg, 'r', encoding='utf-8') as f:
					data = yaml.safe_load(f) or {}
					default.update(data)
			except Exception as e:
				print(f"Warning loading config: {e}")
		return default

	def _run_git(self, args: list) -> str:
		try:
			res = subprocess.run(['git'] + args, cwd=self.repo_root, capture_output=True, text=True, check=True)
			return res.stdout
		except subprocess.CalledProcessError as e:
			print(f"git failed: {' '.join(e.cmd)} -> {e.stderr}")
			return ''

	def should_include_contributor(self, contributor: str) -> bool:
		m = re.search(r'<([^>]+)>', contributor)
		if m and m.group(1) in self.config.get('ignore_emails', []):
			return False
		lower = contributor.lower()
		if 'bot' in lower or 'dependabot' in lower:
			return False
		return True

	def get_pr_contributors(self) -> Set[str]:
		if not (self.pr_base_sha and self.pr_head_sha):
			print('PR SHAs not set; returning empty set')
			return set()
		out = self._run_git(['log', '--use-mailmap', '--format=%aN <%aE>', f'{self.pr_base_sha}..{self.pr_head_sha}'])
		return {l.strip() for l in out.splitlines() if l.strip() and self.should_include_contributor(l.strip())}

	def get_all_contributors(self) -> Set[str]:
		out = self._run_git(['log', '--use-mailmap', '--format=%aN <%aE>', '--all'])
		return {l.strip() for l in out.splitlines() if l.strip() and self.should_include_contributor(l.strip())}

	def parse_citation_cff(self) -> Set[str]:
		path = self.repo_root / 'CITATION.cff'
		if not path.exists():
			return set()
		try:
			with open(path, 'r', encoding='utf-8') as f:
				data = yaml.safe_load(f) or {}
			authors = data.get('authors', [])
			result = set()
			for a in authors:
				if isinstance(a, dict):
					name = None
					if 'given-names' in a and 'family-names' in a:
						name = f"{a.get('given-names')} {a.get('family-names')}"
					elif 'name' in a:
						name = a.get('name')
					if name:
						email = a.get('email')
						if email:
							result.add(f"{name} <{email}>")
						else:
							result.add(name)
				elif isinstance(a, str):
					result.add(a)
			return result
		except Exception as e:
			print(f"Failed to parse CITATION.cff: {e}")
			return set()

	def parse_codemeta_json(self) -> Set[str]:
		path = self.repo_root / 'codemeta.json'
		if not path.exists():
			return set()
		try:
			with open(path, 'r', encoding='utf-8') as f:
				data = json.load(f)
			result = set()
			for fld in ['author', 'contributor', 'maintainer']:
				authors = data.get(fld, [])
				if not isinstance(authors, list):
					authors = [authors]
				for a in authors:
					if isinstance(a, dict):
						name = a.get('name') or (a.get('givenName', '') + ' ' + a.get('familyName', '')).strip()
						if name:
							email = a.get('email')
							if email:
								result.add(f"{name} <{email}>")
							else:
								result.add(name)
					elif isinstance(a, str):
						result.add(a)
			return result
		except Exception as e:
			print(f"Failed to parse codemeta.json: {e}")
			return set()

	def normalize_contributor_name(self, s: str) -> str:
		s = re.sub(r'<[^>]+>', '', s)
		return ' '.join(s.split()).lower()

	def find_missing_contributors(self, pr_contribs: Set[str], metadata_contribs: Set[str]) -> Set[str]:
		meta_norm = {self.normalize_contributor_name(m): m for m in metadata_contribs}
		missing = set()
		for p in pr_contribs:
			if self.normalize_contributor_name(p) not in meta_norm:
				missing.add(p)
		return missing

	def create_comment_body(self, missing: Set[str]) -> str:
		lines = '\n'.join(f"- {m}" for m in sorted(missing))
		return ("⚠️ **Metadata check: contributors missing from citation files**\n\n"
				"The following contributors from this PR are not listed in the metadata files:\n\n"
				f"{lines}\n\n"
				"Next steps:\n- Add them to `CITATION.cff` / `codemeta.json` or update `.mailmap` if these are aliases.\n")

	def post_pr_comment(self, missing: Set[str]) -> bool:
		if not requests:
			print('requests not installed; skipping post')
			return False
		if not (self.github_token and self.github_repo and self.pr_number):
			print('Missing GitHub env variables; cannot post comment')
			return False
		url = f"https://api.github.com/repos/{self.github_repo}/issues/{self.pr_number}/comments"
		headers = {'Authorization': f'token {self.github_token}', 'Accept': 'application/vnd.github.v3+json'}
		try:
			r = requests.post(url, headers=headers, json={'body': self.create_comment_body(missing)})
			r.raise_for_status()
			print('Posted PR comment')
			return True
		except Exception as e:
			print(f'Failed to post PR comment: {e}')
			return False

	def check_contributors(self) -> bool:
		pr_contribs = self.get_pr_contributors()
		print(f'Found {len(pr_contribs)} contributors in PR commits')
		for c in sorted(pr_contribs):
			print(f'  - {c}')
		metadata = self.parse_citation_cff() | self.parse_codemeta_json()
		missing = self.find_missing_contributors(pr_contribs, metadata)
		if missing:
			print(f'Missing contributors: {sorted(missing)}')
			self.post_pr_comment(missing)
			return False if self.config.get('mode') == 'fail' else True
		print('All PR contributors present in metadata')
		return True

	def check_all_contributors_in_metadata(self) -> bool:
		allc = self.get_all_contributors()
		metadata = self.parse_citation_cff() | self.parse_codemeta_json()
		missing = self.find_missing_contributors(allc, metadata)
		if missing:
			print(f'Missing contributors in repo: {sorted(missing)}')
			return False
		print('All contributors present in metadata files')
		return True


def main() -> None:
	checker = ContributorChecker()
	test_mode = not all([checker.pr_base_sha, checker.pr_head_sha, checker.pr_number])
	try:
		if test_mode:
			print('Running in test mode')
			ok = checker.check_all_contributors_in_metadata()
		else:
			print('Running in PR mode')
			ok = checker.check_contributors()
		sys.exit(0 if ok else 1)
	except Exception as e:
		print(f'Error: {e}')
		sys.exit(1)


if __name__ == '__main__':
	main()
