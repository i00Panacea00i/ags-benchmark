# Split extra help item computing with help record rendering

I maintain [Click Extra, a drop-in replacement for Click which adds colorization]( of the help screen.

I am currently relying on finicky regular expressions to identify and match the extra items that are displayed at the end of each option's help. These extra items are rendered in square brackets and looks like:
- `[default: None]`
- `[default: (unlimited)]`
- `[env var: COLOR_CLI8_TIME; default: no-time]`
- and a variety of other formats.

The problem is that the generation of these extra items are deeply embedded within Click and are impossible to fetch independently.

That's why I propose a simple refactor of the `Option.get_help_record()` method, and split it in two:
- a new method to compute the values of these extra items
- keep the original `get_help_record()` as-is, but dedicated to help message rendering only

I have a PR that is ready at #2517.