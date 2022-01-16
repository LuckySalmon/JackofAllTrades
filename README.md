# Jack of All Trades

## What's going on here?

_Jack of All Trades_ is (going to be) a _Pokémon_-style fighting game with physics simulation in place of RNGs. Players will collect and customize "Jacks" for use in battle against other "Jacks". Each "Jack" will be themed around a different profession (or "trade", if you will) and have unique abilities, such as attacks, buffs, and movements. The effectiveness of these abilities will be in part based on the physical positions of the characters in battle, leading (hopefully) to more varied scenarios than there otherwise would be. Currently, every aspect of the game is in the early stages of development.

The game is written in Python using [Panda3D](https://www.panda3d.org/).

## Why?

Y'know how some people are named Jack? But, like, other people are also named Jack? How do you know which one is the real Jack? Trial by combat, of course.
The name is a sort of play on words. It doesn't make much sense if you think about it too hard, but why would you do that?
It's written in Python because Python is neat. Also, it was the only programming language any of us had any significant experience with at the time.
The purpose of the physics simulation is to convert mathematics into slapstick humor.

## Where is it headed?

Development is just now picking up speed, and the next goal is to have a somewhat playable prototype for the game. As such, current and near-future areas of work include:

* Graphics and rendering
* Completion of the character ragdolls/skeletons
* Connecting the physics simulation to gameplay
* Basic GUIs for battles and character management
* An AI for a single player to battle against
* More options for actions a fighter can take in battle
* Refinement and expansion of available characters and abilities

## How would one contribute?

Keep in mind that, currently, *there is no game*. Regardless, the basic steps for helping/testing are:

1. Install [Python 3](https://www.python.org/downloads/)
2. Clone this repository (if you're unfamiliar with or new to Git, [GitHub Desktop](https://docs.github.com/en/get-started/using-github/github-desktop) makes this fairly easy)
3. Make a [virtual environment](https://docs.python.org/3/tutorial/venv.html)
4. Use `pip install -r requirements.txt`
5. Run `JackofAllTrades.py` (soon to be `main.py`)
