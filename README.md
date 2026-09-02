# kubectl by example

Imperative `kubectl` commands, one section at a time, with real output from a local cluster.

The sections follow the order of the [KodeKloud CKAD course](https://kodekloud.com/courses/certified-kubernetes-application-developer-ckad/). Each folder has a short README with the commands, what they do, a screenshot of the output where it helps, and the YAML that `--dry-run` generates.

## Sections

| # | Topic | Blog post |
|---|-------|-----------|
| 01 | [Pods](01-pods/README.md) | [kubectl by example, part 1: pods](https://danieldias.dev/en/blog/kubectl-by-example-part-1-pods) |

## Reproducing the output

Every screenshot comes from a throwaway [kind](https://kind.sigs.k8s.io/) cluster:

```bash
kind create cluster --name ckad
# run the commands from a section
kind delete cluster --name ckad
```

## Diagrams

Drawn with the skill in [`.claude/skills/daniel-diagram`](.claude/skills/daniel-diagram/SKILL.md): a JSON spec (Excalidraw-compatible) rendered with rough.js and captured as PNG. Each section keeps the spec, the HTML source and the image.

## License

[MIT](LICENSE)
