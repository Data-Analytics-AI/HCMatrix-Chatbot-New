from module.doc_preprocessor import (
    download_pdf_and_chunk_with_metadata,
    store_chunks_in_chromadb,
)

database_path = "new_vectorstore"
collection_name = "rag-docs"
directory = "policy_docs"  # Specify the directory where the PDF should be saved

blob_urls = [
    "https://hcmatrix3storageaccount.blob.core.windows.net/hcmatrix3/8947800940280848-DRESS%20CODE%20POLICY.pdf?sv=2023-11-03&se=2124-10-31T15%3A51%3A42Z&sr=b&sp=racwd&sig=b9kYTxvKSGFxOmedItrcf1cHo%2FLEQuh90B3%2BnJHavlY%3D",
    "https://hcmatrix3storageaccount.blob.core.windows.net/hcmatrix3/1741635764083862-HANDOVER%20POLICY%20FEB%202023.pdf?sv=2023-11-03&se=2124-10-31T16%3A08%3A33Z&sr=b&sp=racwd&sig=YM7XHhnolzItW%2BQsfcCF7JEVycJKJ%2BjILRhF%2F6RT9m4%3D",
    "https://hcmatrix3storageaccount.blob.core.windows.net/hcmatrix3/08885024452173984-LEARNING%20AND%20DEVELOPMENT%20APPENDICES.pdf?sv=2023-11-03&se=2124-10-31T16%3A10%3A18Z&sr=b&sp=racwd&sig=Cw%2B174jDfjlrvOxSF9HuCHBC7NQrEd2mPZ2GHA7irUA%3D",
    "https://hcmatrix3storageaccount.blob.core.windows.net/hcmatrix3/5217776437259749-SALES%20TARGET%20ATTAINMENT%20POLICY.pdf?sv=2023-11-03&se=2124-10-31T16%3A15%3A15Z&sr=b&sp=racwd&sig=NiDR%2F%2BFInxpStTfZCl5fsCrIogOQdlSRUCf0tfCyErE%3D",
    "https://hcmatrix3storageaccount.blob.core.windows.net/hcmatrix3/5217776437259749-SALES%20TARGET%20ATTAINMENT%20POLICY.pdf?sv=2023-11-03&se=2124-10-31T16%3A15%3A15Z&sr=b&sp=racwd&sig=NiDR%2F%2BFInxpStTfZCl5fsCrIogOQdlSRUCf0tfCyErE%3D",
    "https://hcmatrix3storageaccount.blob.core.windows.net/hcmatrix3/8450829898983412-SNAPNET%20ANTI%20BRIBERY-ANTI%20CORRUPTION-ANTI%20MONEY%20LAUNDERING%20POLICY.pdf?sv=2023-11-03&se=2124-10-31T16%3A20%3A32Z&sr=b&sp=racwd&sig=P6Ru1aqXUooUiFRFm60AN22oqLfpy%2FwrABoo%2BhiqwHI%3D",
]

for pdf_url in blob_urls:
    # Download the PDF from the URL and extract chunks
    chunks = download_pdf_and_chunk_with_metadata(
        url=pdf_url, directory=directory, company_id="1"
    )
    store_chunks_in_chromadb(chunks=chunks, persist_directory=database_path)
