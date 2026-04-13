alter table change_requests
  add column if not exists override_input_value_info text;
