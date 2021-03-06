from collections import defaultdict, deque
import numpy as np
from scipy import stats

AVERAGE_MODES = ["rolling", 'tiled']
STAT_MODES = ["mean", "min_max", "std_dev", "quantile", "histogram"]


class SummaryCache:
    def __init__(self, mode="tiled", default_stats="std_dev", window: int = None):
        """

        :param mode:
        :param window: the rolling average window under rolling mode
        """
        self.mode = mode
        if mode == "rolling":
            self.data = defaultdict(lambda: deque(maxlen=window))
        elif mode == "tiled":
            assert window is None, "shouldn't specify window under tiled mode"
            self.data = defaultdict(list)
        else:
            raise KeyError(f'mode `{mode}` is not supported. Allowed modes: {AVERAGE_MODES}.')
        self.default_states = default_stats

    def __bool__(self):
        """returns True if any of the values is non-empty."""
        for v in self.data.values():
            if bool(v):
                return True
        return False

    def store(self, metrics=None, **key_values):
        """
        Store the metric data for making the summary later. This allows the logging/saving
        of training metrics asynchronously from the logging.

        :param metrics: (mapping) a mapping of metrics key/values. Will be destructured and appended
                        to the data store one key/value at a time,
        :param ** key_values: (Any) key/value arguments, each being a metric key / metric value pair.
        :return: None
        """
        keys = []
        if metrics:
            key_values.update(metrics)
        for k, v in key_values.items():
            self.data[k].append(v)
            keys.append(k)
        return keys

    def summarize(self, force_clear=None, key_modes=None, **_key_modes):
        """
        | summarizes the statistics, and clears the data store if
        |     1. `force_clear` is set to True
        |       OR
        |     2. the cache is under `tiled` mode.
        |
        | Note that this method is NOT Idempotent. Clears the data store if not using rolling average.
        | Because of this, summarize does not support explicit mode of `get_stats`. The summary
        | of all metric fields are returns when calling this method.
        |
        :param force_clear: (bool) forces clear the data store
        :param key_modes: (dict) a dictionary for the key and the statistic modes to be returned.
        :param _key_modes: (**) key value pairs, as a short hand for the key_modes dictionary.
        :return: dictionary of the keys and the statistics requested.
        """
        _ = self.get_stats(key_modes=key_modes, **_key_modes)
        if force_clear or self.mode == "tiled":
            self.clear()
        return _

    def clear(self):
        self.data.clear()

    def peek(self, *keys, len=5):
        """
        returns truncated version of the cached metrics, useful for taking a peek of
        what is saved in the dataset at the moment.

        :param keys:
        :param len:
        :return:
        """
        return {k: self.data[k][:len] for k in (keys or self.data.keys()) if self.data[k] != []}

    # note: is idempotent
    def get_stats(self, *only_keys, explicit=None, key_modes=None, **_key_modes):
        """
        | Returns the metrics as a dictionary containing key / value pairs
        | of the statistics of the metrics.
        |
        | OR
        |
        | Returns statistics that are queried.
        |
        | Note that this method is idempotent. AKA you can call multiple times without
        | affecting what is stored in the data object.
        |
        | When a few key strings are passed in explicitly, ONLY those keys
        | plus those specified in the keyword arguments in **key_modes are
        | returned.
        |
        | To enable explicit mode without specifying *only_keys, set
        | `get_only` to True
        |
        | # Modes for the Statistics:
        | ===================
        |
        | key_mode would be one of:
        |   - mean:
        |   - min_max:
        |   - std_dev:
        |   - quantile:
        |   - histogram(bins=10):
        |
        :param * only_keys: list of key strings to return explicitly
        :param explicit: boolean flag, when true only keys explicitly specified would be returned
        :param key_modes: a dictionary for the key and the statistic modes to be returned.
        :param ** _key_modes: key value pairs, as a short hand for the key_modes dictionary.
        :return: dictionary of the keys and the statistics requested.
        """
        explicit = explicit or len(only_keys) > 0
        key_modes = key_modes or dict()
        key_modes.update(_key_modes)
        metrics = dict()
        keys = {*only_keys, *key_modes.keys()} if explicit else self.data.keys()
        for k in keys:
            mode = key_modes.get(k, self.default_states)
            if k not in self.data:
                continue
            else:
                d = np.array(self.data[k])
                if mode.startswith("mean"):
                    metrics[k + "/mean"] = d.mean(axis=0)
                elif mode.startswith("min_max"):
                    metrics[k + "/min"] = d.min(axis=0)
                    metrics[k + "/max"] = d.max(axis=0)
                    metrics[k + "/mean"] = d.mean(axis=0)
                elif mode.startswith("std_dev"):
                    metrics[k + "/stddev"] = np.std(d, axis=0)
                    metrics[k + "/mean"] = d.mean(axis=0)
                    mode = stats.mode(d, axis=0)[0][0]
                    metrics[k + "/mode"] = mode
                elif mode.startswith("quantile"):
                    metrics[k + "/0"] = np.percentile(d, 0, axis=0)
                    metrics[k + "/25"] = np.percentile(d, 25, axis=0)
                    metrics[k + "/mean"] = np.percentile(d, 50, axis=0)
                    metrics[k + "/75"] = np.percentile(d, 75, axis=0)
                    metrics[k + "/100"] = np.percentile(d, 100, axis=0)
                elif mode.startswith("histogram"):
                    # note: need make bin number configurable
                    metrics[k + "/hist"], metrics[k + "/divs"] = np.histogram(d.flatten(), bins=10)
        return metrics
