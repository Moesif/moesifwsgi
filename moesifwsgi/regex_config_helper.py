import re


class RegexConfigHelper:

    def __init__(self):
        pass

    @classmethod
    def prepare_config_mapping(cls, event):
        """
        Function to prepare config mapping
        Args:
            event: Event to be logged
        Return:
            regex_config: Regex config mapping
        """
        regex_config = {}

        # Config mapping for request.verb
        if event.request.verb:
            regex_config["request.verb"] = event.request.verb

        # Config mapping for request.uri
        if event.request.uri:
            extracted = re.match(r"http[s]*://[^/]+(/[^?]+)", event.request.uri)
            if extracted is not None:
                route_mapping = extracted.group(1)
            else:
                route_mapping = '/'
            regex_config["request.route"] = route_mapping

        # Config mapping for request.ip_address
        if event.request.ip_address:
            regex_config["request.ip_address"] = event.request.ip_address

        # Config mapping for response.status
        if event.response.status:
            regex_config["response.status"] = event.response.status

        return regex_config

    @classmethod
    def regex_match(cls, event_value, condition_value):
        """
        Function to perform the regex matching with event value and condition value
        Args:
            event_value: Value associated with event (request)
            condition_value: Value associated with the regex config condition
        Return:
             regex_matched: Regex matched value to determine if the regex match was successful
        """
        extracted = re.search(condition_value, event_value)
        if extracted is not None:
            return extracted.group(0)

    def fetch_sample_rate_on_regex_match(self, regex_configs, config_mapping):
        """
        Function to fetch the sample rate and determine if request needs to be block or not
        Args:
            regex_configs: Regex configs
            config_mapping: Config associated with the request
        Return:
            sample_rate: Sample rate
        """
        # Iterate through the list of regex configs
        for regex_rule in regex_configs:
            # Fetch the sample rate
            sample_rate = regex_rule["sample_rate"]
            # Fetch the conditions
            conditions = regex_rule["conditions"]
            # Bool flag to determine if the regex conditions are matched
            regex_matched = None
            # Create a table to hold the conditions mapping (path and value)
            condition_table = {}
            # Iterate through the regex rule conditions and map the path and value
            for condition in conditions:
                # Add condition path -> value to the condition table
                condition_table[condition["path"]] = condition["value"]
            # Iterate through conditions table and perform `and` operation between each conditions
            for path, values in condition_table.items():
                # Check if the path exists in the request config mapping
                if config_mapping[path]:
                    # Fetch the value of the path in request config mapping
                    event_data = config_mapping[path]
                    # Perform regex matching with event value
                    regex_matched = self.regex_match(event_data, values)
                else:
                    # Path does not exists in request config mapping, so no need to match regex condition rule
                    regex_matched = False
                # If one of the rule does not match, skip the condition & avoid matching other rules for the same condition
                if not regex_matched:
                    break
            # If regex conditions matched, return sample rate
            if regex_matched:
                return sample_rate
        # If regex conditions are not matched, return sample rate as None and will use default sample rate
        return None
