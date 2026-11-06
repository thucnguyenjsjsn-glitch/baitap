import heapq
from collections import defaultdict
from fastapi import HTTPException
from app.plan_schemas import PlanExtracted

def validate_plan(plan: PlanExtracted) -> dict:
    ids = [t.id for t in plan.tasks]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, 'ID công việc bị trùng')
    id_set = set(ids)
    edges = set()
    for dep in plan.dependencies:
        if dep.before not in id_set or dep.after not in id_set:
            raise HTTPException(422, f'Quan hệ chứa ID không tồn tại: {dep.before} -> {dep.after}')
        if dep.before == dep.after:
            raise HTTPException(422, f'Công việc tự phụ thuộc: {dep.before}')
        edges.add((dep.before, dep.after))
    return {'valid': True, 'task_count': len(ids), 'dependency_count': len(edges), 'duplicate_dependencies_ignored': len(plan.dependencies)-len(edges)}

def find_cycle(nodes, graph):
    state = {x: 0 for x in nodes}
    for root in sorted(nodes):
        if state[root]: continue
        stack = [(root, iter(sorted(graph[root])))]
        state[root] = 1
        path = [root]
        positions = {root:0}
        while stack:
            node, neighbors = stack[-1]
            try: nxt = next(neighbors)
            except StopIteration:
                state[node] = 2
                positions.pop(node, None)
                path.pop()
                stack.pop()
                continue
            if state[nxt] == 1:
                return path[positions[nxt]:] + [nxt]
            if state[nxt] == 0:
                state[nxt] = 1
                positions[nxt] = len(path)
                path.append(nxt)
                stack.append((nxt, iter(sorted(graph[nxt]))))
    return []

def order_plan(plan: PlanExtracted) -> dict:
    meta = validate_plan(plan)
    ids = [t.id for t in plan.tasks]
    graph = defaultdict(set)
    indegree = {x:0 for x in ids}
    for dep in plan.dependencies:
        if dep.after not in graph[dep.before]:
            graph[dep.before].add(dep.after)
            indegree[dep.after] += 1
    ready = [x for x in ids if indegree[x] == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        x = heapq.heappop(ready)
        result.append(x)
        for y in graph[x]:
            indegree[y] -= 1
            if indegree[y] == 0: heapq.heappush(ready,y)
    if len(result) != len(ids):
        cycle = find_cycle(ids,graph)
        return {'status':'cycle_detected', 'order':None, 'cycle':cycle, 'reason':'Phát hiện vòng phụ thuộc; cần sửa trước khi lập thứ tự', 'validation':meta}
    return {'status':'ordered', 'order':result, 'cycle':[], 'reason':'Thứ tự hợp lệ theo quan hệ trước–sau, chọn ID alphabet khi cùng sẵn sàng', 'validation':meta}
