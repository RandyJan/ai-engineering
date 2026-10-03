from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim


# Load an embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


policies = [
    "Employees are entitled to 15 vacation leave days every calendar year.",

    "Overtime work requires approval from the employee's supervisor.",

    "Employees must submit their Daily Time Record before the fifth day of the following month.",

    "Sick leave may be used when an employee is unable to work because of illness.",

    "Remote work requires prior approval from the employee's supervisor.",
]


# Convert all policies into vectors
policy_embeddings = model.encode(
    policies,
    convert_to_tensor=True,
)


question = input("Ask a question: ")


# Convert the user's question into a vector
question_embedding = model.encode(
    question,
    convert_to_tensor=True,
)


# Compare the question against every policy
scores = cos_sim(
    question_embedding,
    policy_embeddings,
)[0]


results = []

for index, score in enumerate(scores):
    results.append(
        {
            "policy": policies[index],
            "score": float(score),
        }
    )


# Highest similarity first
results.sort(
    key=lambda item: item["score"],
    reverse=True,
)


print("\nSearch Results:\n")

best_match = results[0]

print("\nBest Match:")
print(
    f"Score: {best_match['score']:.4f}"
)
print(
    f"Policy: {best_match['policy']}"
)