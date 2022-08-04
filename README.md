# Kindly Kappa

## Backend

The backend was made using [fastapi](https://fastapi.tiangolo.com/) and [starlette](https://www.starlette.io/). To get started:

1. Clone the repository (or you can also download it as a .zip and extract it if you don't have git installed):
   `git clone https://github.com/Vthechamp22/kindly-kappa.git`
2. Install the dependencies (using a [virtual environment](https://realpython.com/python-virtual-environments-a-primer/) is recommended):
   `pip install -r requirements.txt`
3. Start the backend by opening a terminal in the root folder, and then running
   `uvicorn server.main:app`
   If you want to test the backend, you can create a dummy frontend by running
   `python -m websockets ws://localhost:8000/room`
4. We have also used [snekbox](https://github.com/python-discord/snekbox) to handle the evaluation of code. To start it up, first make sure you have [docker](https://www.docker.com/) installed. Then run
   `docker run --ipc=none --privileged -p 8060:8060 ghcr.io/python-discord/snekbox`
   > NOTE: You might need to run this command with `sudo`

The backend is now up and running!

## Frontend

The frontend for this project was made using Vite and Vue. In order to run it, you need to first install node. This project has been tested with v16.16.0, v17.2 and v18.6.0

1.  - Windows: Go to [nodejs.org](https://nodejs.org) and install the latest LTS version of node. (≥ 16.16.0)
    - Linux:
      1.  You can use a node version manager like [fnm](https://github.com/Schniz/fnm) or [nvm](https://github.com/nvm-sh/nvm)
      2.  Use it to install the latest LTS version (`fnm install --lts` or `nvm install --lts`)
2.  Spin up a new shell and move into the `frontend` folder.
3.  Install all the dependencies by running
    `npm install`
4.  Run the project by running
    `npm run dev`
