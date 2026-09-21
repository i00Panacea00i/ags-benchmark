# _is_incomplete_option incorrectly processes last_option in loop

The _is_incomplete_option function in the Click library has a logic issue in its loop that sets the last_option variable. The function does not break the loop after assigning last_option, which leads to wrong shell completion.


## Replication: 
See 
### RCA: 
We can reproduce issue If we have flag option before tuple option

## Environment:

- Python version: 3.11
- Click version: 8.1.7

## Possible solution :

Once we identify the last option we have the break the loop in _is_incomplete_option function

```python .numberLines
def _is_incomplete_option(ctx: Context, args: t.List[str], param: Parameter) -> bool:
    """Determine if the given parameter is an option that needs a value.

    :param args: List of complete args before the incomplete value.
    :param param: Option object being checked.
    """
    if not isinstance(param, Option):
        return False

    if param.is_flag or param.count:
        return False

    last_option = None

    for index, arg in enumerate(reversed(args)):
        if index + 1 > param.nargs:
            break

        if _start_of_option(ctx, arg):
            last_option = arg
            break  # <-------------------------------------------------- break the loop on finding the option

    return last_option is not None and last_option in param.opts

```