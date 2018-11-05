import importlib
import copy
import traceback

from . import inputs as mod_inputs
from . import filters as mod_filters
from . import outputs as mod_outputs


class MonitorBeat(object):
    def __init__(self, config):
        self.config = config

        self.inputs = {
            conf["name"]: self.create_instance(mod_inputs, conf["handler"],
                                               conf.get("options", None))
            for conf in config["inputs"]
        }
        self.filters = {
            conf["name"]: self.create_instance(mod_filters, conf["handler"],
                                               conf.get("options", None))
            for conf in config["filters"]
        }
        self.outputs = {
            conf["name"]: self.create_instance(mod_outputs, conf["handler"],
                                               conf.get("options", None))
            for conf in config["outputs"]
        }

    def create_instance(self, mod, cls_name, options):
        cls = getattr(mod, cls_name, None)
        if cls is None:
            raise Exception("无法加载'{}'".format(cls_name))

        return cls(options)

    def get_event_queue(self):
        for inp_conf in self.config["inputs"]:
            name = inp_conf["name"]
            tags_out = inp_conf.get("tags_out", [])

            inp = self.inputs[name]
            try:
                for event in inp:
                    event.update({"tags": tags_out, "input": name})
                    yield event
            except:
                traceback.print_exc()

    def get_output_queue(self, event_queue):
        last_event_queue = list(event_queue)
        for flt_conf in self.config["filters"]:
            new_event_queue = last_event_queue[:]

            tags_in = flt_conf.get("tags_in", None)
            for event in last_event_queue:
                # 比较事件的tags和过滤器的tags，如果没有交集，则跳过
                if tags_in is not None:
                    if not set(event.get("tags", [])) & set(tags_in):
                        continue

                name = flt_conf["name"]
                flt = self.filters[name]

                try:
                    for handled_event in flt(event):
                        new_event = {}
                        new_event.update(event)
                        new_event.update(handled_event)
                        new_event = copy.deepcopy(new_event)
                        new_event["filter"] = name
                        new_event["tags"] = flt_conf.get("tags_out", [])

                        new_event_queue.append(new_event)
                except:
                    traceback.print_exc()

            last_event_queue = new_event_queue

        return last_event_queue

    def beat(self):
        event_queue = self.get_event_queue()
        output_queue = self.get_output_queue(event_queue)

        count = 0
        for event in output_queue:
            for out_conf in self.config["outputs"]:
                out = self.outputs[out_conf["name"]]
                tags_in = out_conf["tags_in"]
                if set(event.get("tags", [])) & set(tags_in):
                    try:
                        out(event)
                    except:
                        traceback.print_exc()
                    else:
                        count += 1

        return count
