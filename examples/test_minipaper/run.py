from model import TestModel


def main():
    print("Running Test Mini-Paper Model...")
    model = TestModel()
    for i in range(5):
        print(f"Step {i + 1}")
        model.step()
    print("Test run completed successfully.")


if __name__ == "__main__":
    main()
