from collections import deque
from dataclasses import dataclass
from torch.profiler import DeviceType

class EventKey:
    def __init__(self, event):
        self.event = event

    def __hash__(self):
        return hash(self.event.id)
    
    def __eq__(self, other):
        return self.event.id == other.event.id

    def __repr__(self):
        return f"<{self.event.name()} id={self.event.correlation_id} start={self.event.start_time_ns}>"
        
@dataclass
class EventMetrics:
    self_time_ns: int = 0
    idle_time_ns: int = 0

def compute_event_metrics(prof) -> dict[EventKey, EventMetrics]:
    metrics = dict()
    compute_self_time(prof, metrics)
    compute_idle_time(prof, metrics)
    return metrics

def compute_self_time(prof, metrics):
    '''
    Computes event's self time (total time - time in child ops).

        Parameters:
            event_tree: Profiler's kineto_results.experimental_event_tree
    '''
    stack = deque()
    event_tree = prof.profiler.kineto_results.experimental_event_tree()
    for event in event_tree:
        stack.append(event)

    # standard iterating dfs
    while stack:
        curr_event = stack.pop()
        self_time = curr_event.duration_time_ns
        if curr_event.children:
            for child_event in curr_event.children:
                self_time - child_event.duration_time_ns
                stack.append(child_event)
        if EventKey(curr_event) in metrics:
            metrics[EventKey(curr_event)].self_time_us = self_time
        else:
            metrics[EventKey(curr_event)] = EventMetrics(self_time_ns=self_time)

def compute_idle_time(prof, metrics):
    event_tree = prof.profiler.kineto_results.experimental_event_tree()
    event_list = prof.profiler.kineto_results.events()
    
    def is_cuda_launch_kernel(e):
        return e.name() == "cudaLaunchKernel"
    # TODO: find a better way to identify cudaLaunchKernel
    def is_cuda_kernel(e):
        return e.device_type() == DeviceType.CUDA and e.name() != "[memory]" and e.name() != "Memset (Device)"


    # Record All the idle intervals
    queue_depth = 0
    idle_interval = []
    cuda_kernel_events = [event for event in event_list if is_cuda_launch_kernel(event) or is_cuda_kernel(event)]
    cuda_kernel_events.sort(key=lambda e: e.start_us())

    if len(cuda_kernel_events) == 1:
        return
    for i in range(1, len(cuda_kernel_events)):
        prev_event = cuda_kernel_events[i-1]
        curr_event = cuda_kernel_events[i]
        if (is_cuda_launch_kernel(prev_event)):
            queue_depth += 1
        if (is_cuda_kernel(prev_event)):
            queue_depth -= 1
        if (prev_event.start_us() + prev_event.duration_us()) < curr_event.start_us() and queue_depth == 0:
            idle_interval.append((prev_event.start_us() + prev_event.duration_us(), curr_event.start_us()))
        #print(f"{prev_event.name()} {prev_event.start_us()} {prev_event.start_us() + prev_event.duration_us()} {queue_depth}") 
    
    # For every event, compute the absolute idle time and the percentage idle time
    # idle_interval Seems correct
    for event in event_list:
        for interval in idle_interval:
            pass

        
    

            

        
    
