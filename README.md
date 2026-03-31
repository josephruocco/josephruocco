# GitHub Branch Counter

This generates a custom contribution-style SVG from `git log --all`, so commits that only exist on non-default branches still appear in a branch-aware heatmap.

## Usage

Run the generator from the repo you want to measure:

```bash
python3 generate_graph.py
```

It writes the output to `assets/branch-contributions.svg`.

## Automate It

The included GitHub Actions workflow regenerates the SVG every day and on manual runs, then commits the updated asset back into the repo.

## Embed In A Profile README

If this repo is your special profile repo named exactly after your GitHub username, add this to `README.md`:

```md
![Branch contributions](assets/branch-contributions.svg)
```

## Notes

- This is custom output, not GitHub's official profile contributions graph.
- GitHub's real profile graph still only counts commits that land on the default branch or `gh-pages`.
