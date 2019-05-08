from moesifapi.models import *
from moesifapi.exceptions.api_exception import *
from moesifapi.api_helper import *


class Company:

    def update_company(self, company_profile, api_client, DEBUG):
        if not company_profile:
            print('Expecting the input to be either of the type - CompanyModel, dict or json while updating company')
        else:
            if isinstance(company_profile, dict):
                if 'company_id' in company_profile:
                    try:
                        api_client.update_company(CompanyModel.from_dictionary(company_profile))
                        if DEBUG:
                            print('Company Profile updated successfully')
                    except APIException as inst:
                        if 401 <= inst.response_code <= 403:
                            print("Unauthorized access sending event to Moesif. Please check your Appplication Id.")
                        if DEBUG:
                            print("Error while updating company, with status code:")
                            print(inst.response_code)
                else:
                    print('To update an company, an company_id field is required')

            elif isinstance(company_profile, CompanyModel):
                if company_profile.company_id is not None:
                    try:
                        api_client.update_company(company_profile)
                        if DEBUG:
                            print('Company Profile updated successfully')
                    except APIException as inst:
                        if 401 <= inst.response_code <= 403:
                            print("Unauthorized access sending event to Moesif. Please check your Appplication Id.")
                        if DEBUG:
                            print("Error while updating company, with status code:")
                            print(inst.response_code)
                else:
                    print('To update a company, a company_id field is required')
            else:
                try:
                    company_profile_json = APIHelper.json_deserialize(company_profile)
                    if 'company_id' in company_profile_json:
                        try:
                            api_client.update_company(CompanyModel.from_dictionary(company_profile_json))
                            if DEBUG:
                                print('Company Profile updated successfully')
                        except APIException as inst:
                            if 401 <= inst.response_code <= 403:
                                print("Unauthorized access sending event to Moesif. Please check your Appplication Id.")
                            if DEBUG:
                                print("Error while updating company, with status code:")
                                print(inst.response_code)
                    else:
                        print('To update a company, an company_id field is required')
                except:
                    print('Error while deserializing the json, please make sure the json is valid')

    def update_companies_batch(self, company_profiles, api_client, DEBUG):
        if not company_profiles:
            print('Expecting the input to be either of the type - List of CompanyModel, dict or json while updating companies')
        else:
            if all(isinstance(company, dict) for company in company_profiles):
                if all('company_id' in company for company in company_profiles):
                    try:
                        batch_profiles = [CompanyModel.from_dictionary(d) for d in company_profiles]
                        api_client.update_companies_batch(batch_profiles)
                        if DEBUG:
                            print('Company Profile updated successfully')
                    except APIException as inst:
                        if 401 <= inst.response_code <= 403:
                            print("Unauthorized access sending event to Moesif. Please check your Appplication Id.")
                        if DEBUG:
                            print("Error while updating companies, with status code:")
                            print(inst.response_code)
                else:
                    print('To update companies, an company_id field is required')

            elif all(isinstance(company, CompanyModel) for company in company_profiles):
                if all(company.company_id is not None for company in company_profiles):
                    try:
                        api_client.update_companies_batch(company_profiles)
                        if DEBUG:
                            print('Company Profile updated successfully')
                    except APIException as inst:
                        if 401 <= inst.response_code <= 403:
                            print("Unauthorized access sending event to Moesif. Please check your Appplication Id.")
                        if DEBUG:
                            print("Error while updating companies, with status code:")
                            print(inst.response_code)
                else:
                    print('To update companies, an company_id field is required')
            else:
                try:
                    company_profiles_json = [APIHelper.json_deserialize(d) for d in company_profiles]
                    if all(isinstance(company, dict) for company in company_profiles_json) and all(
                                    'company_id' in user for user in company_profiles_json):
                        try:
                            batch_profiles = [CompanyModel.from_dictionary(d) for d in company_profiles_json]
                            api_client.update_companies_batch(batch_profiles)
                            if DEBUG:
                                print('Company Profile updated successfully')
                        except APIException as inst:
                            if 401 <= inst.response_code <= 403:
                                print("Unauthorized access sending event to Moesif. Please check your Appplication Id.")
                            if DEBUG:
                                print("Error while updating companies, with status code:")
                                print(inst.response_code)
                    else:
                        print('To update companies, an company_id field is required')
                except:
                    print('Error while deserializing the json, please make sure the json is valid')
