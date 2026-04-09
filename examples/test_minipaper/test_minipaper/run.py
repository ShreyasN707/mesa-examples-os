from .model import MinipaperModel

if __name__ == "__main__":
    model = MinipaperModel()
    for _ in range(5):
        model.step()
    print("Minipaper Example Executed Successfully!")
