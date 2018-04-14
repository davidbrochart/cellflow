from IPython.core.magic import Magics, magics_class, line_cell_magic, cell_magic
import shlex

@magics_class
class Cellflow(Magics):

    def __init__(self, shell):
        super(Cellflow, self).__init__(shell)
        self.flow = {}
        self.verbose = False

    @line_cell_magic
    def cellflow_configure(self, line, cell=None):
        if not cell:
            cell = ''
        txt = shlex.split((line + ' ' + cell).replace('\n', ' '))
        args = {k: True if v.startswith('-') else v for k,v in zip(txt, txt[1:]+['--']) if k.startswith('-')}
        self.verbose = args.get('-v', False)
        if self.verbose:
            print('Verbose mode enabled')

    @cell_magic
    def onchange(self, line, cell):
        '''
        Syntax is:
        
        %%onchange a, b -> c, d
        ...code for the computation...
        
        Means if a or b change, c and d will be computed through the cell code.
        '''
        i = line.find('->')
        if i < 0:
            i = len(line)
            outputs = []
        else:
            outputs = line[i+2:].replace(',', ' ').split()
        inputs = line[:i].replace(',', ' ').split()
        for varname in outputs:
            if varname not in self.flow:
                self.flow[varname] = {}
            self.flow[varname]['in'] = {i:[] for i in inputs}
            self.flow[varname]['out'] = outputs
            self.flow[varname]['code'] = cell

    @line_cell_magic
    def compute(self, line, cell=None):
        '''
        Syntax is:
        
        %compute c, d
        
        or:
        
        %%compute c, d
        ...additional code (like result printing)...
        
        Will figure out the data flow and optimally compute the results.
        '''
        varnames = line.replace(',', ' ').split()
        log = ''
        paths = [[varname] for varname in varnames]
        # back-trace all variables to be computed
        done = False
        while not done:
            done = True
            i_path = 0
            while i_path < len(paths):
                path = paths[i_path]
                varname = path[0] # source variable
                has_dep = False
                if varname in self.flow: # variable depends on other variable(s)
                    for dep in self.flow[varname]['in']:
                        has_dep = True
                        paths.append([dep] + path)
                        done = False
                    if has_dep:
                        del paths[i_path]
                if not has_dep:
                    i_path += 1
        log += 'The data flow consists of all the following paths:\n'
        for path in paths:
            log += ' -> '.join(path) + '\n'
        log += '\n'
        # compute results in an optimal way
        computed = []
        done = False
        while not done:
            done = True
            i_path = 0
            while i_path < len(paths):
                path = paths[i_path]
                done2 = False
                while not done2:
                    if len(path) == 1:
                        done2 = True
                    else:
                        varname = path[1]
                        log += f'Looking at variable {varname} in path: {" -> ".join(path)}\n'
                        done2 = True
                        dep = path[0]
                        var_last = self.flow[varname]['in'][dep]
                        var_new = self.shell.user_ns[dep]
                        if var_last:
                            if dep in self.shell.user_ns:
                                if var_last[0] != self.shell.user_ns[dep]:
                                    changed = True
                                    log += f"Variable {dep} has changed from {var_last[0]} to {var_new}\n"
                                    var_last[0] = var_new
                                else:
                                    changed = False
                            else:
                                changed = True # but variable will be unknown...
                                self.flow[varname]['in'][dep] = []
                        else:
                            # dependency didn't exist, so a computation is required
                            changed = True
                            if dep in self.shell.user_ns:
                                self.flow[varname]['in'][dep] = [var_new]
                            else:
                                # variable will be unknown...
                                pass
                        if (len(path) > 1) and ((varname in computed) or (not changed)):
                            # variable has not changed, or the computation has already been done.
                            # this path does not need to re-compute the next variable.
                            # other paths might need to, this ensures that if any input changes
                            # the outputs are re-computed.
                            log += 'No computation required\n\n'
                            del path[0]
                            if len(path) == 1:
                                done2 = True
                            else:
                                done2 = False
                if len(path) == 1:
                    # target variable does not need to be re-computed through this path, then delete the path
                    del paths[i_path]
                else:
                    # next variable must be re-computed, but we need to update all its dependencies before
                    # doing the computation, otherwise the computation will be done several times.
                    other_paths = [p for i, p in enumerate(paths) if i != i_path]
                    do_compute = True
                    for p in other_paths:
                        if varname in p:
                            i = p.index(varname)
                            if i != 0:
                                log += f'Variable {varname} is also in path: {" -> ".join(p)}\n'
                                # variable has another dependency, through another path
                                if i > 1:
                                    # and this dependency has dependencies, so let's update them first.
                                    # this means forgetting this path for now, we will come back to it later.
                                    log += 'And other variables have to be computed first\n'
                                    done = False
                                    do_compute = False
                                    break
                                else:
                                    log += "Which doesn't prevent computing it\n"
                    if do_compute:
                        # do the computation
                        log += 'Computing:\n'
                        log += self.flow[varname]['code'] + '\n'
                        self.shell.ex(self.flow[varname]['code'])
                        computed += self.flow[varname]['out']
                        del path[0]
                    i_path += 1
                    log += '\n'
        log += 'All done!'
        if self.verbose:
            print(log)
        if cell:
            self.shell.ex(cell)
