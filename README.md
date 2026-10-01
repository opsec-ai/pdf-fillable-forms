# pdf-fillable-forms

Turns static PDF forms into forms you can actually type into.

You know those PDFs - applications, registrations, membership forms - that print
beautiful blank lines and tick boxes, but give you no way to fill them out on
your computer? This skill takes your PDF, finds every blank line, checkbox, and
Yes/No pair, and lays invisible text fields over them so you can type directly
into the form and save it. The page keeps its original printed look: no white
boxes, no borders, and your text sits right on the lines.

## What is Crush?

[Crush](https://github.com/charmbracelet/crush) is an AI coding agent that runs
in your terminal (from the makers of Glow, Gum, and the rest of the Charm
toolkit). Crush works through reusable **skills** - folders of instructions and
scripts that teach it how to do a job well. This repository is one such skill.

## Setup: install this as a skill

To use it, copy to your agent's skills folder, or tell it to do it for you:

> Set this repo up as a skill so you can make PDF forms fillable:
> clone (or copy) it into your skills directory as `pdf-fillable-forms`,
> following your skill setup instructions.

Not using crush? Tell your agent to convert it.

Skill setup instructions live in the [Crush repository](https://github.com/charmbracelet/crush).
Once installed, just hand the agent a form PDF and say something like:
"make this editable so I can type in it".

## Requirements

The agent will need, at runtime:

- Python 3 with `pdfplumber`, `pypdf`, `pypdfium2`, `Pillow`, `numpy`
- Node.js with `pdf-lib`
- `qpdf` (optional, used to validate the output)

Technical stuff, for coding nerds & agents like me is in [AGENTS.md](AGENTS.md).

## License

This project is licensed under the [GNU Affero General Public License v3.0](./LICENSE).

Need different terms - permissive licensing, commercial use, or something
custom? Contact the author: find them on

[GitHub](https://github.com/themanyone) or reach out via

- GitHub https://github.com/themanyone
- YouTube https://www.youtube.com/themanyone
- Mastodon https://mastodon.social/@themanyone
- Linkedin https://www.linkedin.com/in/henry-kroll-iii-93860426/
- Buy me a coffee https://buymeacoffee.com/isreality
- [TheNerdShow.com](http://thenerdshow.com/)

Copyright (C) 2026 Henry Kroll III, www.thenerdshow.com.
See [LICENSE](LICENSE) for details.
