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
For example:
`# noqa F841`,
`# noqa : F841`,
and `# noqa:  F841`
will be interpreted as `# noqa`
and may, as a result,
hide other errors you care about.

This plugin looks for noqa comments
that do not match the proper formatting
so your `# noqa` comments work and do only what you expect them to.

Optionally, it can also enforce usage of codes with all `# noqa` comments.

In addition, this plugin looks for `# noqa` comments that are unnecessary
because either there are no matching violations on the line
or they contain codes that do not match existing violations.

Errors reported by this module cannot be prevented via `# noqa` comments,
otherwise you'd never see many of the errors it produces.
Use `ignore`, `extend-ignore`, or `per-file-ignores` to ignore them as needed.
Alternatively, if you have a comment that this plugin thinks is a
`# noqa` with codes,
but isn't,
e.g. `# noqa : X100 is not a code`,
you can make the comment look less like a proper `# noqa` comment.
e.g. `# noqa - X100 is not a code`
(flake8 will interpret both of those as `# noqa`).

Usage Note:
When determining if violations have matched a `# noqa` comment,
this plugin requires flake8 to have been made aware of the violations
that would otherwise apply.
Some plugins do their own processing of `# noqa` comments 
and stop sending violation reports to flake8 when they see a `# noqa` comment.
A plugin doing so will cause this plugin to stop seeing the violation,
and it may report the lack of a violation or matching code.
When you then remove the `# noqa` comment or violation code, 
the other plugin will resume sending the violation,
prompting you to restore the `# noqa` comment or code.

The best fix for this situation is to try to get the offending plugin
to stop respecting `# noqa` comments.
A plugin doing so is considered an anti-pattern,
and it's best to allow flake8 to determine if violations should be 
surfaced to the user or not.
The offending plugin may have an option to control this behavior
(note the flake8 `--disable-noqa` option will disable *all* noqa comments,
so is not a suitable fix for this situation).
If the plugin does not have an option to control its `# noqa` behavior, 
the best course of action may be to contact the maintainers of 
the plugin via the appropriate issue reporting system.

If the plugin is unmaintained,
or the maintainers decline to address the issue for whatever reason,
feel free to file an issue on this plugin
to see if a work-around can be established.


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
: Include plugin name in messages

`noqa-no-include-name`
: Do not include plugin name in messages (default setting)

All options may be specified on the command line with a `--` prefix,
or can be placed in your flake8 config file.


Error Codes
-----------

| Code   | Message |
|--------|---------|
| NQA001 | "`#noqa`" must have a single space after the hash, e.g. "`# noqa`" |
| NQA002 | "`# noqa X000`" must have a colon, e.g. "`# noqa: X000`" |
| NQA003 | "`# noqa : X000`" must not have a space before the colon, e.g. "# noqa: X000"' |
| NQA004 | "<code># noqa:&nbsp;&nbsp;X000</code>" must have at most one space before the codes, e.g. "`# noqa: X000`" |
| NQA005 | "`# noqa: X000, X000`" has duplicate codes, remove X000 |
| NQA011 | "`#flake8: noqa`" must have a single space after the hash, e.g. "`# flake8: noqa`" |
| NQA012 | "`# flake8 noqa`" must have a colon or equals, e.g. "`# flake8: noqa`" |
| NQA013 | "`# flake8 : noqa`" must not have a space before the colon, e.g. "# flake8: noqa" |
| NQA101 | "`# noqa`" has no violations |
| NQA102 | "`# noqa: X000`" has no matching violations |
| NQA103 | "`# noqa: X000, X001`" has unmatched code(s), remove X001 |
| NQA104 | "`# noqa`" must have codes, e.g. "`# noqa: X000`" (enable via `noqa-require-code`) |


Examples
--------

```
#flake8 noqa   <-- ignored (NQA011)
x = 1+2  #noqa  <-- ignored (NQA001)
x = 1+2  # noqa E226  <-- treated as a blanket noqa (NQA002)
x = 1+2  # noqa : E226  <-- treated as a blanket noqa (NQA003)
x = 1+2  # noqa:  E226  <-- treated as a blanket noqa (NQA004)
x = 1+2 # noqa: X101, E261 <-- unmatched code (NQA103)
```
