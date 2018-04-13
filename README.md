Cellflow is an IPython cell-based dataflow automation tool. Its API is built upon the following magic functions:

```python
%%onchange a, b -> c, d
c = f1(a, b)
d = f2(a, b)

%%compute c, d
print(f'c = {c}')
print(f'd = {d}')
```
