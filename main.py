import argparse
from karaoke_generator import create


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path", help="ruta del video")
    return parser.parse_args()


def main():
    args = parse_arguments()
    print(f"Creando karaoke: {args.video_path}")
    res = create(args.video_path)


if __name__ == "__main__":
    main()
