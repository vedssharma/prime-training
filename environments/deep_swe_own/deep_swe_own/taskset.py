"""DeepSWE v1.1 on task images copied into your own Prime registry namespace.

Prime VM sandboxes (required: DeepSWE tasks run offline) only boot images the account
owns. Copy the upstream images first:
`prime images transfer-bulk -m <manifest> --platform linux/amd64`.
"""

from collections.abc import Iterator

import verifiers.v1 as vf
from deep_swe.taskset import DeepSWEConfig, DeepSWETask, DeepSWETaskset
from verifiers.v1.tasksets.harbor import HarborTaskset


class DeepSWEOwnConfig(DeepSWEConfig):
    image_namespace: str = "prime/vedshar"
    """Registry namespace holding the copied `swe-bench-202605:<tag>` images."""


class DeepSWEOwnTaskset(DeepSWETaskset, vf.Taskset[DeepSWETask, DeepSWEOwnConfig]):
    def load(self) -> Iterator[DeepSWETask]:
        for task in HarborTaskset.load(self):
            if task.data.verifier is None:
                raise RuntimeError("DeepSWE v1.1 requires Harbor separate-verifier support")
            name = task.data.image.rsplit("/", 1)[-1]
            data = task.data.model_copy(update={"image": f"{self.config.image_namespace}/{name}"})
            yield DeepSWETask(data, task.config)
