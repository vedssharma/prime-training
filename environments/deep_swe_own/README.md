# deep-swe-own

`primeintellect/deep-swe` (DeepSWE v1.1) with task images read from your own Prime registry namespace (`taskset.image_namespace`, default `prime/vedshar`). Prime VM sandboxes only boot images the account owns, and DeepSWE needs VMs because its tasks run offline.

Copy each task's upstream image first (the destination keeps the `swe-bench-202605:<tag>` name):

```zsh
prime images transfer-bulk -m images.jsonl --platform linux/amd64
# images.jsonl: {"source": "public.ecr.aws/d3j8x8q7/swe-bench-202605:<tag>"}
```
