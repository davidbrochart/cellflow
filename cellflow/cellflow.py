from IPython.core.magic import Magics, magics_class, line_cell_magic, cell_magic
import shlex
import pickle
import hashlib

@magics_class
class Cellflow(Magics):

    def __init__(self, shell):
        super(Cellflow, self).__init__(shell)
        self.flow = {}
        self.log = ''
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
        deps = {i:None for i in inputs} # shared data between output variables of a cell
                                        # so that it updates automatically
        for varname in outputs:
            if varname not in self.flow:
                self.flow[varname] = {}
            self.flow[varname]['in'] = deps
            self.flow[varname]['out'] = outputs
            self.flow[varname]['code'] = cell

    def fingerprint(self, varname):
        pkl = pickle.dumps(self.shell.user_ns[varname])
        hasher = hashlib.md5()
        hasher.update(pkl)
        return hasher.hexdigest()

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
        self.log = ''
        paths = [[varname] for varname in varnames]
        # back-trace all variables to be computed and get all possible paths to them
        has_dep = True
        while has_dep:
            has_dep = False
            i_path = 0
            while i_path < len(paths):
                path = paths[i_path]
                varname = path[0] # input variable
                has_dep = False
                if varname in self.flow: # variable depends on other variable(s)
                    has_dep = True
                    for dep in self.flow[varname]['in']:
                        paths.append([dep] + path)
                    del paths[i_path]
                if not has_dep:
                    i_path += 1
        self.log += 'The data flow consists of the following paths:\n'
        for path in paths:
            self.log += ' -> '.join(path) + '\n'
        # compute results in an optimal way
        done = False
        while not done:
            done = True
            i_path = 0
            while i_path < len(paths):
                # let's see first if dependencies have other dependencies
                other_paths = [p for i, p in enumerate(paths) if i != i_path]
                do_compute = True
                path = paths[i_path]
                varname = path[1] # target
                dep = path[0] # dependency
                self.log += f'\nLooking at target variable {varname} in path: {" -> ".join(path)}\n'
                for p in other_paths:
                    if varname in p:
                        i = p.index(varname)
                        if i != 0:
                            self.log += f'Variable {varname} is also in path: {" -> ".join(p)}\n'
                            # variable has another dependency, through another path
                            if i > 1:
                                # and this dependency has dependencies, so let's update them first.
                                # this means skipping this path, we will come back to it later.
                                self.log += 'And other variables have to be computed first\n'
                                done = False
                                do_compute = False
                                break
                            else:
                                self.log += "Which doesn't prevent computing it\n"

                if do_compute:
                    # this path doesn't have to wait for other paths,
                    # now let's see if dependencies have changed.
                    var_last = self.flow[varname]['in'][dep]
                    if dep in self.shell.user_ns:
                        var_new = self.fingerprint(dep)
                    else:
                        var_new = None
                    if var_last:
                        if var_new:
                            if var_last != var_new:
                                changed = True
                            else:
                                changed = False
                        else:
                            changed = True # but variable will be unknown...
                            self.flow[varname]['in'][dep] = None
                    else:
                        # dependency didn't exist, so a computation is required
                        changed = True
                    if changed:
                        self.log += f'Variable {dep} has changed\n'
                    if not changed:
                        # dependency has not changed, no computation required for this path
                        do_compute = False
                        self.log += 'No change in dependencies\n'
                        del path[0]
                if do_compute:
                    # do the computation
                    self.log += 'Computing:\n'
                    self.log += self.flow[varname]['code'] + '\n'
                    self.shell.ex(self.flow[varname]['code'])
                    # save dependency fingerprints for this computation, so that nothing happens if no change in dependencies.
                    # this also prevents further execution of this cell through other paths, since it was already done.
                    for i in self.flow[varname]['in']:
                        self.flow[varname]['in'][i] = self.fingerprint(i)
                    del path[0]
                if len(path) == 1:
                    del paths[i_path]
                else:
                    i_path += 1
        self.log += '\nAll done!'
        if self.verbose:
            print(self.log)
        if cell:
             self.shell.ex(cell)
