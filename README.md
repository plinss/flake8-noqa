[flake8-noqa](https://github.com/plinss/flake8-noqa)
==========

flake8 plugin to validate `# noqa` comments.

flake8 is very particular about formatting of `# noqa` comments.
If your `# noqa` isn't exactly what flake8 expects, 
it can easily cause your `# noqa` comment to be ignored.

However, forgetting a colon or adding an extra space in the wrong place
will turn a strict `# noqa: <code>` comment 
into a blanket `# noqa` comment,
which is likely not what you intended.
For example: `# noqa F841`
will be interpreted as `# noqa`
and may hide other errors you care about.

This plugin looks for noqa comments 
that do not match the proper formatting
so your `# noqa` comments work and do only what you expect them to.

Optionally, it can also enforce usage of codes with all `# noqa` comments.

In addition, this plugin looks for `# noqa` comments that are unnecessary
because either there are no matching violations on the line
or they contain codes that do not match existing violations.

Errors reported by this module cannot be prevented via `# noqa` comments,
otherwise you'd never see many of the errors it produces.
Use `ignore`, `extend-ignore`, or `per-file-ignores` to ignore them.


Installation
------------

Standard python package installation:

    pip install flake8-noqa


Options
-------
`noqa-require-code`
: Require code(s) to be included in  `# noqa` comments

`noqa-no-require-code`
: Do not require code(s) in `# noqa` comments (default setting)

`noqa-include-name`
: Include plugin name in messages (default setting)

`noqa-no-include-name`
: Remove plugin name from messages

All options may be specified on the command line with a `--` prefix,
or can be placed in your flake8 config file.


Error Codes
-----------

| Code   | Message |
|--------|---------|
| NQA001 | "`#noqa`" must have a single space after the hash, e.g. "`# noqa`" |
| NQA002 | "`# noqa X000`" must have a colon, e.g. "`# noqa: X000`" |
| NQA003 | "`# noqa:  X000`" must have at most one space before the codes, e.g. "`# noqa: X000`" |
| NQA004 | "`# noqa: X000, X000`" has duplicate codes, remove X000 |
| NQA010 | "`#flake8: noqa`" must have a single space after the hash, e.g. "`# flake8: noqa`" |
| NQA011 | "`# flake8 noqa`" must have a colon or equals, e.g. "`# flake8: noqa`" |
| NQA101 | "`# noqa`" has no violations |
| NQA102 | "`# noqa: X000`" has no matching violations |
| NQA103 | "`# noqa: X000, X001`" has unmatched code(s), remove X001 |
| NQA104 | "`# noqa`" must have codes, e.g. "`# noqa: X000`" (enable via `noqa-require-code`) |



Examples
--------

```
#flake8 noqa   <-- ignored (NQA010)
x = 1+2  #noqa  <-- ignored (NQA001)
x = 1+2  # noqa E226  <-- treated as a blanket noqa (NQA002)
x = 1+2  # noqa:  E226  <-- treated as a blanket noqa (NQA003)
x = 1+2 # noqa: X101, E261 <-- unmatched code (NQA103)
```