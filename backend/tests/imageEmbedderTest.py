from main.src.utils.core.ai.imageEmbedder import SigLIPEmbedder


if __name__ == "__main__":

    model = SigLIPEmbedder()

    vec = model.embed(r"C:\Users\ranaw\Downloads\unnamed (1).jpg")
    vec2 = model.embed(r"C:\Users\ranaw\Downloads\unnamed (1).jpg")
    vec3 = model.embed(r"C:\Users\ranaw\Downloads\unnamed (1).jpg")

    print("Embedding dimension:", len(vec))
    print(vec[:10])
    print("Embedding dimension:", len(vec2))
    print(vec2[:10])
    print("Embedding dimension:", len(vec3))
    print(vec3[:10])
