# Algorithms & DSA

The system utilizes several Data Structures and Algorithms to ensure efficient real-time face recognition and data processing.

## 1. Vector Search for Face Recognition

- **Data Structure:** High-Dimensional Vector (Array of floats)
- **Algorithm:** Cosine Similarity

When a face is detected, it is converted into a 128/512 dimension embedding vector. To recognize the face, we calculate the cosine similarity against all enrolled vectors.

* **Time Complexity:** O(N * D) where N is the number of students and D is the dimensionality of the vector.
* **Space Complexity:** O(N * D) to hold embeddings in memory.

## 2. In-Memory Hash Table for Caching

- **Data Structure:** Hash Table (Dictionary)
- **Algorithm:** Hash Lookup

To prevent querying the SQLite database for every frame of a video feed, student embeddings are loaded into a Hash Table at startup (`Dict[student_id, embedding_vector]`).

* **Time Complexity:** O(1) average lookup.
* **Space Complexity:** O(N) where N is the number of enrolled students.

## 3. Queue for Event Processing

- **Data Structure:** FIFO Queue (via `asyncio.Queue`)

The Event-Driven portion relies on an asynchronous Queue. When events like `FaceRecognized` fire rapidly, they are pushed to the back of the queue, ensuring the system doesn't drop attendance processing under high load.

* **Time Complexity:** O(1) for enqueue and dequeue.
* **Space Complexity:** O(E) where E is the number of pending events.
