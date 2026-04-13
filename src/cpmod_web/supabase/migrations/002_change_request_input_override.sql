alter table change_requests
  add column if not exists override_input_data_filename text,
  add column if not exists override_input_data_storage_path text;
