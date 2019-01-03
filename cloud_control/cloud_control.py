import builder 

def get_settings():
  root_parser = builder.arg_parser()
  root_parser.description = 'cloud_control is an application for managing cloud'
    ' infrastructure in the enterprise. It interfaces with other known tooling'
    ' like Terraform, GitHub and Jira. It does this rather than try to create' 
    ' something new so as to maintain clear delegation of duties but also'
    ' allowing cross-functional working by keeping different functions separated'
    ' in reusable modules'
  
  def add_deploy_parser(parser):
    d_parser = parser.add_parser('deploy', 
      help='deploy configuration to the cloud')
    d_parser.formatter_class = RawTextHelpFormatter
    return d_parser.add_argument('cloud'
      choices=('all', 'aws', 'gcp', 'triton'))
  
  def add_config_parser(parser):
    c_parser = parser.add_parser('config', 
      help='Administer cloud configuration on respective repository')
    c_parser.formatter_class = RawTextHelpFormatter
    c_parser.add_argument('-h', '--github')
    return d_parser.add_argument('c_action'
      choices=('create', 'delete', 'update'))
      
  mgmt_parser = root_parser.add_subparsers(
    help='manage infrastructure deployment or infrastructure configuration',
    dest='command')
    
  add_deploy_parser(mgmt_parser)
  add_config_parser(mgmt_parser)
  
  return root_parser.parse_args()
  

def get_files(org, repo_name, directory, file_type_fn):
  pass
  
  
def main():
  settings = get_settings()
  if settings.deploy:
    import deployer as deploy 
    import checker as check
    config_org = builder.get_org(settings, settings.config_org)
    code_org = builder.get_org(settings, settings.code_org)
    settings.cloud == 'gcp':
      config_files = get_files(config_org, settings.project_id, 'gcp', 
                              __config_files)
      code_files = get_files(code_org, settings.project_id, 'gcp', 
                              __code_files)
      check.gcp(config_files)
      deploy(settings, config_files, code_files)
  elif settings.config:
    import github_project_creator


if __name__ = '__main__':
  main()
