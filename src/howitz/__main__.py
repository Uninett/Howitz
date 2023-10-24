from .endpoints import app
from .config import Config, cliargs


if __name__ == '__main__':
    parser = cliargs.make_argument_parser()
    args = cliargs.parse_args(parser)
    config = Config.from_args(args)
    app.run(host=str(config.listen), port=config.port)
