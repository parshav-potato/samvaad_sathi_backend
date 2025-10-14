import sys


def main() -> None:
    # Ensure local package resolution
    sys.path.append('.')
    # Run misc
    import scripts.smoke_misc as misc
    misc.main()
    # Run golden path
    import scripts.smoke_golden_path as golden
    golden.main()
    # Run re-attempt scenarios
    import scripts.smoke_reattempt as reattempt
    reattempt.main()
    # Run security
    import scripts.smoke_security as sec
    sec.main()


if __name__ == "__main__":
    main()


