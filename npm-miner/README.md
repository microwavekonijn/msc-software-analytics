# NPM miner

## Requirements

- Node v20
- Pnpm
- Mongo database

## Preparation

Copy `.env.example` to `.env` and fill in the values

## Usage

Run:

```bash
$ pnpm tsx ./miner.ts
```

To run in the background continuously use:

```bash
$ nohup pnpm tsx ./miner.ts > output.txt &
```