import json
import re
from moesifapi import APIException
from functools import reduce

def get_field_value_for_path(path, request_fields = {}, request_body = {}):
  if path and path.startswith('request.body.'):
    return request_body.get(path.replace('request.body.', ''), None)
  return request_fields.get(path, None)

def does_regex_config_match(regex_config, request_fields, request_body):
  if not regex_config:
    return True

  def does_one_condition_match(condition):
    path = condition['path']
    field_value = get_field_value_for_path(path, request_fields, request_body)
    regex_pattern = condition['value']
    if field_value:
      return re.match(regex_pattern, field_value)
    else:
      return False

  def does_one_set_of_conditions_match(one_regex_config):
    conditions = one_regex_config['conditions']
    if not conditions:
      return False
    values_to_and = map(does_one_condition_match, conditions)
    return reduce(lambda x, y: x and y, values_to_and, True)

  values_to_or = map(does_one_set_of_conditions_match, regex_config)
  return reduce(lambda x, y: x or y, values_to_or, False)


class GovernanceRulesManager:
  def __init__(self, api_client):
    self.api_client = api_client
    self.user_rules = {}
    self.company_rules = {}
    self.regex_rules = []
    self.unidentified_user_rules = []
    self.unidentified_company_rules = []

  def get_governance_rules_from_client(self, DEBUG):
    try:
      get_rules_response = self.api_client.get_governance_rules()
      rules = json.loads(get_rules_response.raw_body)
      self.cache_rules(rules)
      return rules
    except APIException as inst:
      if 401 <= inst.response_code <= 403:
        print("[moesif] Unauthorized access getting application configuration. Please check your Appplication Id.")
      if DEBUG:
        print("[moesif] Error getting governance rules, with status code:", inst.response_code)
      return None
    except Exception as ex:
      if DEBUG:
        print("[moesif] Error getting governance rules:", ex)
      return None

  def cache_rules(self, rules):
    self.user_rules = {}
    self.company_rules = {}
    self.regex_rules = []
    self.unidentified_user_rules = []
    self.unidentified_company_rules = []
    for rule in rules:
      if rule['type'] == 'regex':
        self.regex_rules.append(rule)
      elif rule['type'] == 'user':
        self.user_rules[rule['_id']] = rule
        if rule['applied_to_unidentified']:
          self.unidentified_user_rules.append(rule)
      elif rule['type'] == 'company':
        self.company_rules[rule['_id']] = rule
        if rule['applied_to_unidentified']:
          self.unidentified_company_rules.append(rule)

  def get_applicable_regex_rules(self, request_fields, request_body):
    if self.regex_rules:
      return filter(lambda rule: does_regex_config_match(rule['regex_config'], request_fields, request_body), self.regex_rules)
    else:
      return [];

  def get_applicable_unidentified_user_rules(self, request_fields, request_body):
    if self.unidentified_user_rules:
      return filter(lambda rule: does_regex_config_match(rule['regex_config'], request_fields, request_body), self.unidentified_user_rules)
    else:
      return [];

  def get_applicable_unidentified_company_rules(self, request_fields, request_body):
    if self.unidentified_company_rules:
      return filter(lambda rule: does_regex_config_match(rule['regex_config'], request_fields, request_body), self.unidentified_company_rules)
    else:
      return [];

  def get_user_rules(self, config_rules_values, request_fields, request_body):
    applicable_rules = []
    in_cohort_of_rule_hash = {}

    # if there is entry in config_rules_values it means user is in the cohort of the rule.

    if config_rules_values:
      for rules_values_entry in config_rules_values:
        rule_id = rules_values_entry['rules']
        in_cohort_of_rule_hash[rule_id] = True

        found_rule = self.user_rules[rule_id]
        if not found_rule:
          # print an debug log here.
          break



        regex_matched = does_regex_config_match(found_rule['regex_config'], request_fields, request_body)

        if not regex_matched:
          break

        if found_rule['applied_to'] == 'not_matching':
          # skipping because apply to user not in cohort
          break
        else:
          applicable_rules.append(found_rule)


    # now handle where user is not in cohodrt.
    for rule in self.user_rules.items():
      if rule['applied_to'] == 'not_matching' and not in_cohort_of_rule_hash[rule['_id']]:
        regex_matched = does_regex_config_match(rule['regex_config'], request_fields, request_body)
        if regex_matched:
          applicable_rules.append(rule)

    return applicable_rules


  def get_company_rules(self, config_rules_values, request_fields, request_body):
    applicable_rules = []
    in_cohort_of_rule_hash = {}

    # if there is entry in config_rules_values it means user is in the cohort of the rule.
    if config_rules_values:
      for rules_values_entry in config_rules_values:
        rule_id = rules_values_entry['rules']
        in_cohort_of_rule_hash[rule_id] = True

        found_rule = self.company_rules[rule_id]
        if not found_rule:
          # print an debug log here.
          break



        regex_matched = does_regex_config_match(found_rule['regex_config'], request_fields, request_body)

        if not regex_matched:
          break

        if found_rule['applied_to'] == 'not_matching':
          # skipping because apply to user not in cohort
          break
        else:
          applicable_rules.append(found_rule)


    # now handle where user is not in cohort.
    for rule in self.company_rules.items():
      if rule['applied_to'] == 'not_matching' and not in_cohort_of_rule_hash[rule['_id']]:
        regex_matched = does_regex_config_match(rule['regex_config'], request_fields, request_body)
        if regex_matched:
          applicable_rules.append(rule)

    return applicable_rules









