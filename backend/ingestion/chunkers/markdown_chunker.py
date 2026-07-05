from langchain.text_splitter import RecursiveCharacterTextSplitter


def chunk_markdown(markdown_content: str, metadata: dict) -> list[dict]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_text(markdown_content)

    result = []
    for i, chunk_text in enumerate(chunks):
        result.append(
            {
                "chunk_id": f"{metadata['hash']}_chunk_{i}",
                "document_url": metadata["url"],
                "agency": metadata["agency"],
                "category": metadata.get("category", "General"),
                "document_title": metadata["title"],
                "text": chunk_text,
            }
        )
    return result
