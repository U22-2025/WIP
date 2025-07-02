import os
import ast
from collections import defaultdict

ROOT = os.path.abspath('.')

class FunctionCollector(ast.NodeVisitor):
    def __init__(self):
        self.stack = []
        self.functions = []
        self.calls = defaultdict(list)

    def visit_FunctionDef(self, node):
        func_name = '.'.join(self.stack + [node.name])
        self.functions.append((func_name, node.lineno))
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            called = node.func.id
        elif isinstance(node.func, ast.Attribute):
            called = node.func.attr
        else:
            called = None
        if called:
            current = '.'.join(self.stack) if self.stack else '<module>'
            self.calls[current].append(called)
        self.generic_visit(node)

def analyze_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return [], {}
    collector = FunctionCollector()
    collector.visit(tree)
    return collector.functions, collector.calls

def find_py_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))
    return py_files

def sanitize(name):
    return name.replace('/', '_').replace('.', '_').replace('-', '_')

def build_graph(py_files):
    func_to_file = {}
    functions = {}
    calls_map = defaultdict(list)

    for path in py_files:
        rel = os.path.relpath(path, ROOT)
        funcs, calls = analyze_file(path)
        for func_name, lineno in funcs:
            full_name = f"{rel}:{func_name}"
            func_to_file[func_name] = full_name
            functions[full_name] = {'file': rel, 'name': func_name}
        for caller, callees in calls.items():
            caller_full = f"{rel}:{caller}" if caller != '<module>' else f"{rel}:<module>"
            for callee in callees:
                calls_map[caller_full].append(callee)

    edges = []
    for caller, callees in calls_map.items():
        for callee in callees:
            callee_full = func_to_file.get(callee)
            if callee_full:
                edges.append((caller, callee_full))
    return functions, edges

def make_mermaid(functions, edges, output):
    by_dir = defaultdict(lambda: defaultdict(list))
    for full_name, info in functions.items():
        dirpath = os.path.dirname(info['file'])
        by_dir[dirpath][info['file']].append(full_name)

    lines = ['```mermaid', 'graph TD']

    def add_subgraph(path, indent=0):
        dirs = sorted([d for d in by_dir.keys() if os.path.dirname(d)==path and d!=path])
        files = [f for f in by_dir.get(path, {})]
        for d in dirs:
            lines.append(' '*(indent)+f'subgraph {sanitize(d)}["{d}"]')
            add_subgraph(d, indent+2)
            lines.append(' '*(indent)+'end')
        for f in files:
            lines.append(' '*(indent)+f'subgraph {sanitize(f)}["{f}"]')
            for func in by_dir[path][f]:
                node_id = sanitize(func)
                func_label = func.split(':',1)[1]
                lines.append(' '*(indent+2)+f'{node_id}["{func_label}"]')
            lines.append(' '*(indent)+'end')

    if by_dir:
        root_dir = os.path.commonpath(list(by_dir.keys()))
        add_subgraph(root_dir)

    for src, dst in edges:
        lines.append(f'{sanitize(src)} --> {sanitize(dst)}')

    lines.append('```')
    with open(output, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def main():
    py_files = find_py_files(ROOT)
    funcs, edges = build_graph(py_files)
    make_mermaid(funcs, edges, 'full_mermaid.md')

    dirs = sorted(set(os.path.dirname(p) for p in py_files))
    for d in dirs:
        rel = os.path.relpath(d, ROOT)
        dir_files = [p for p in py_files if p.startswith(d)]
        if not dir_files:
            continue
        funcs, edges = build_graph(dir_files)
        output = os.path.join(rel, 'mermaid.md')
        make_mermaid(funcs, edges, output)

if __name__ == '__main__':
    main()
