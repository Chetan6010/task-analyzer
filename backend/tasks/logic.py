def detect_cycles(tasks):
    graph = {t["id"]: t.get("dependencies", []) for t in tasks}
    visited, rec_stack = set(), set()
    cycles = set()

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        for dep in graph[node]:
            if dep in rec_stack:
                cycles.add(node)
                cycles.add(dep)
            elif dep not in visited:
                dfs(dep)
        rec_stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return list(cycles)
