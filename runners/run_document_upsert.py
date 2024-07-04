
from data_preprocessing.employee_metadata_extractor import EmployeeIDExtractor
from data_preprocessing.external_file_permission import FilePermissions
from rag_engine.utils import retrieve_document_metadata, pdf_loader
from azure.storage.filedatalake import FileSystemClient
from rag_engine.emdedder import UserDocument
import itertools


def upsert_user_document(pdf_path, metadata):
    chunked_docs = pdf_loader(pdf_path, metadata=metadata)

    user_db_instance = UserDocument()
    user_db_instance(chunked_docs)


def extract_document_metadata_and_permissions(company_id:str, utility_db_file_system: FileSystemClient):

    #### Off-course this could be better (line 20-21)
    ## they could be merged...
    fp = FilePermissions(company_id, utility_db_file_system)
    emp_extractor = EmployeeIDExtractor(company_id, utility_db_file_system)
    docs_metadata = fp.get_company_documents_metadata()    

    all_documents_permission = []
    for metadata in docs_metadata:
        
        department_ids = metadata["departement_ids"]
        group_ids = metadata["group_ids"]
        role_ids = metadata["role_ids"]
        doc_url = metadata["document_url"]
        doc_id = metadata["doc_id"]

        employee_ids_dep    = list(itertools.chain(*[emp_extractor.extract_employee_ids_from_department_id(int(q)) for q in department_ids]))
        employee_ids_group  = list(itertools.chain(*[emp_extractor.extract_employee_ids_from_group_id(int(k)) for k in group_ids]))
        employee_ids_role   = list(itertools.chain(*[emp_extractor.extract_employee_ids_from_role_id(int(v)) for v in role_ids]))

        valid_employee_ids = [*employee_ids_dep, *employee_ids_group, *employee_ids_role]
        all_documents_permission.append({
            "company_id": company_id,
            "document_id": doc_id,
            "document_url": doc_url,
            "employee_ids": valid_employee_ids,
        })

    return all_documents_permission


def execute(company_id:str, utility_db_file_system: FileSystemClient):

    document_permission = extract_document_metadata_and_permissions(company_id, utility_db_file_system)    
    for documents_data in document_permission:
        doc_url = documents_data.pop("document_url")
        upsert_user_document(doc_url, documents_data)