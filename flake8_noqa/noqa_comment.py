"""Filter for errors masked by noqa comments."""

from __future__ import annotations

import re
from typing import ClassVar, Dict, List, Match, Optional, Sequence, TYPE_CHECKING

import flake8.checker
import flake8.defaults
import flake8.options.manager
import flake8.style_guide
import flake8.utils

if (TYPE_CHECKING):
	from tokenize import TokenInfo


NOQA_FILE = re.compile(r'\s*#(?P<flake8>\s*flake8)(?P<sep>\s*[:=])?(?P<noqa>(?:\b|\s*)noqa)', re.IGNORECASE)
NOQA_INLINE = re.compile(r'#(?P<noqa>\s*noqa)\b(?P<sep>\s*:)?(?P<codes>\s*([a-z]+[0-9]+(?:[,\s]+)?)+)?', re.IGNORECASE)


class FileComment:
	"""File scope noqa comment."""

	flake8: str
	sep: str
	noqa: str
	valid: bool
	token: TokenInfo

	@classmethod
	def match(cls, token: TokenInfo) -> Optional[FileComment]:
		"""Create a FileComment if it matches the token."""
		match = NOQA_FILE.match(token.string)
		if (not match):
			return None
		return FileComment(match, token)

	def __init__(self, match: Match, token: TokenInfo) -> None:
		self.flake8 = match.group('flake8')
		self.sep = match.group('sep') or ''
		self.noqa = match.group('noqa')
		self.valid = (flake8.defaults.NOQA_FILE.match(token.string) is not None)
		self.token = token


class InlineComment:
	"""noqa comment info."""

	comments: ClassVar[Dict[str, List[InlineComment]]] = {}

	noqa: str
	sep: str
	codes: str
	valid: bool
	flake8_codes: str
	token: TokenInfo
	start_line: int

	@classmethod
	def match(cls, token: TokenInfo, prev_token: TokenInfo = None) -> Optional[InlineComment]:
		"""Create an InlineComment if it matches the token."""
		match = NOQA_INLINE.search(token.string)
		if (not match):
			return None
		return InlineComment(match, token, prev_token)

	@classmethod
	def add_comment(cls, filename: str, comment: InlineComment) -> None:
		"""Add comment to master list."""
		if (filename not in cls.comments):
			cls.comments[filename] = []
		cls.comments[filename].append(comment)

	@classmethod
	def file_comments(cls, filename: str) -> Sequence[InlineComment]:
		"""Get comments for file."""
		def start_line(comment: InlineComment) -> int:
			return comment.start_line
		return sorted(cls.comments.get(filename, []), key=start_line)

	def __init__(self, match: Match, token: TokenInfo, prev_token: TokenInfo = None) -> None:
		self.noqa = match.group('noqa')
		self.sep = match.group('sep') or ''
		self.codes = match.group('codes') or ''

		flake8_match = flake8.defaults.NOQA_INLINE_REGEXP.search(token.string)
		self.valid = (flake8_match is not None)
		self.flake8_codes = (flake8_match.group('codes') or '') if (flake8_match is not None) else ''

		self.token = token
		self.start_line = prev_token.start[0] if (prev_token is not None) else token.start[0]

	@property
	def end_line(self) -> int:
		"""Get ending line of comment."""
		return self.token.start[0]

	@property
	def text(self) -> str:
		"""Reconstruct comment as text."""
		return f'#{self.noqa}{self.sep}{self.codes}'

	@property
	def code_list(self) -> Sequence[str]:
		"""Get list of all violation codes."""
		return flake8.utils.parse_comma_separated_list(self.codes) if (self.codes) else []

	@property
	def flake8_code_list(self) -> Sequence[str]:
		"""Get list of violation codes honoroed by flake8."""
		return flake8.utils.parse_comma_separated_list(self.flake8_codes) if (self.flake8_codes) else []

	def __repr__(self) -> str:
		"""Debug representation."""
		return f'{self.start_line}-{self.end_line}:{self.codes}'
