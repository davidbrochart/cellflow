Cellflow is an IPython cell-based dataflow automation tool whose API is built with magic functions.

How it works
============

Instead of being fully reactive, as [observable notebooks](https://beta.observablehq.com/) are, cellflow only tries to bring to the Jupyter Notebook (or even the IPython console) a way to link cells to each other. It lets the user specify on which variables a cell will react, and what results it will produce. Based on this information, cellflow will take care of executing the right cell at the right time when a result is asked for. You can think of it as the equivalent of the `make` tool for interactive computing.

```python
%%onchange a, b -> c, d
c = a + b
d = a - b

a = 2
b = 1

%%compute c, d
print(f'c = {c}')
print(f'd = {d}')

# will print:
# c = 3
# d = 1
```

Of course your dataflow can be much more complex. Cellflow won't (re)compute a variable that doesn't need to. If it needs to, cellflow will figure out the least amount of cells that need to be executed, in the right order, based on the sensitivity list provided in the `onchange` statement of each cell.

Installation
============

    $ python setup.py install
