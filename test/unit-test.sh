#!/bin/bash

# This should work on linux and Windows Git Bash

# This uses the HMRC test sandbox
profile=test
gnucash_file=hmrc-test.sqlite3.gnucash
config_file=gnucash-uk-vat-${profile}.json
user_config_file=".${config_file}"
due_date_list=("2017-05-07" "2017-08-07")

# NOTE: This needs updating each time a command is added
valid_commands=( config create-user auth test-fraud show-obligations show-open-obligations show-payments show-liabilities submit-vat-return show-vat-return show-account-summary show-account-detail help )


help_string=$( cat <<HEREDOC
# Overview
Script to launch various commands required to unit-test the gnucash-uk-vat bridging application.

# Requirements
This script assumes that the setup.sh has been run for the gnucash-uk-vat bridging application.
See ../README.md for instruction on how to run the setup.sh.

# Initial setup
The first time the '$0 config' command is run, it checks for:
1. gnucash-uk-vat script
   If this is missing, the 'setup.sh' hasn't been run yet.
   See 'Requirements' section above.
2. User configuration file
   The 'gnucash-uk-vat --init-config' command will use the default values 
   stored in a private User/Profile specific configuration file:
       $HOME/${user_config_file}
   If this file doesnt exist, it creates a new copy from a template.
   IMPORTANT: 
   Update this config file with your private credentials and common configuration:
     a) 'application' section: Add the client credentials for your sandbox application 
        defined on the MTD developer site.
     b) 'accounts' section: Add GnuCash accounts for the test gnucash data 
        file: ${gnucash_file}
        See the config.example.json for the accounts that should be used 
        to test with the ${gnucash_file} data file.
     c) 'identity' section: can be removed, as it is not used to initialise a config.json.

# Create ${config_file}
The test config file can be created or updated using the command:
    '$0 config'
This will create a local config file: ${config_file} 

NOTE: The 'identity.vrn' field can't be populated until there is an 
      application.client-[id|secret]
      See 'Create HMRC User' section below.

# Create Test User
When using the test (sandbox) profile, you will need to create a test user (Don't use your HMRC production credentials!)
    '$0 user'
This creates a user in the MTD system and downloads the users details into user.json
NOTE: This command assumes the application associated with the client-id in 
          ${config_file}
      has been configured to access the 'Create Test User' endpoint 
      in 'API Subscriptions' when viewin application details from here:
      https://developer.service.hmrc.gov.uk/developer/applications

# Update ${config_file} with VRN
After updating the user.json file, update the config file to use the new test VRN.
    '$0 config'

# Authenticate with HMRC
Run this command to authenticate with HMRC MTD sandbox application.:
    '$0 auth'
Open the printed authentication URL in a browser and enter the test MTD account credentials printed in the console.
Once authenticated, the file 'test/auth.json' will be populated with a short lived authentication token.

# Test Fraud Prevention Headers
Run this command to verify that the fraud headers submitted by gnucash-uk-vat 
complies with the HMRC MTD requirements.
    '$0 test-fraud'
A report will be printed to the screen showing any issues it encountered.

NOTE #1: Missing header 'gov-client-multi-factor': A bridge system doesnt generally use MFA.
NOTE #2: This command assumes the application associated with the client-id in 
            ${config_file}
         has been configured to access the 'Test Fraud Prevention Headers' endpoint 
         in 'API Subscriptions' when viewin application details from here:
         https://developer.service.hmrc.gov.uk/developer/applications

# Test show-open-obligations


HEREDOC
)


# Set a default command
command="help"
# If command provided
if [[ ! "$1" == "" ]]; then
    provided_command=$1
    if [[ ${valid_commands[*]} =~ (^|[[:space:]])"${provided_command}"($|[[:space:]]) ]]; then
        command=${provided_command}
    else
        echo "Invalid command '${provided_command}'";
        command_list=$( echo ${valid_commands[*]} | tr " " "\n" )
        echo "Choose from:";
        echo "${command_list}";
        exit 0
    fi
fi

# Check for a json configuration file with user specific configuration 
check_user_config() {
  pushd ${HOME} 2>&1 > /dev/null
  if [[ ! -f ${user_config_file} ]]; then
      # Create the user config file
      if [[ ! -f $(dirname $(which python))/scripts/gnucash-uk-vat ]]; then
        echo "ERROR: Missing python script '$(dirname $(which python))/scripts/gnucash-uk-vat'. Run the setup"
      else
        # Create a default user config file for testing
        python $(dirname $(which python))/scripts/gnucash-uk-vat --init-config --config ${user_config_file} --profile ${profile} --gnucash ${gnucash_file}
        echo "Created: ${HOME}/${user_config_file}"
        echo "Now update the 'accounts' and 'application' stanzas for the environment being tested against"
        echo "These will be used to populate config files used in tests. Missing fields will be ignored."
        echo "Once configured to your requirements, re-run your command."
      fi
      popd 2>&1 > /dev/null
      exit 1
  fi
  popd 2>&1 > /dev/null
}

print_help() {
  echo "$help_string"
}

config() {
  echo "Create config.json..."
  python $(dirname $(which python))/scripts/gnucash-uk-vat --init-config --config ${config_file} --profile ${profile} --gnucash ${gnucash_file}
}

user() {
  echo "Get new test user from MTD API..."
  python -u ./get-test-user --config ${config_file}
}

auth() {
  echo "Get OAuth authentication token from MTD website..."
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --authenticate --config ${config_file}
}

test_fraud() {
  echo "Test Fraud Prevention Headers against MTD website..."
  python -u test-fraud-api
}

show_open_obligations() {
  echo "Test for Open Obligations against MTD website..."
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --show-open-obligations --config ${config_file} --json
}

show_obligations() {
  echo "Show VAT Obligations against MTD website..."
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --show-obligations --config ${config_file} --json
}

show_payments() {
  echo "Show previous Payments against MTD website..."
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --start "2017-01-01"  --end "2017-12-31" --show-payments --config ${config_file} --json
}

show_liabilities() {
  echo "Show current Liabilities against MTD website..."
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --start "2017-01-01"  --end "2017-12-31" --show-liabilities --config ${config_file} --json
}

show_vat_return() {
  echo "Show previous Vat Return against MTD website..."

  due_date_index=${1:-0}
  due_date=${due_date_list[${due_date_index}]}
  
  echo "due_date=${due_date}"

  # Check for vat returns.
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --due-date "${due_date}" --start "2017-01-01"  --end "2017-12-31" --show-vat-return --config ${config_file} --json
}

show_account_summary() {
  echo "Show GnuCash account summary against MTD website..."

  due_date_index=${1:-0}
  due_date=${due_date_list[${due_date_index}]}
  
  echo "due_date=${due_date}"

  # Check for vat returns.
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --due-date "${due_date}" --show-account-summary --config ${config_file} --json
}

show_account_detail() {
  echo "Show GnuCash account details against MTD website..."

  due_date_index=${1:-0}
  due_date=${due_date_list[${due_date_index}]}
  
  echo "due_date=${due_date}"

  # Check for vat returns.
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --due-date "${due_date}" --show-account-detail --config ${config_file} --json
}

submit_vat_return() {
  echo "Submit Vat Return against MTD website..."

  due_date_index=${1:-0}
  due_date=${due_date_list[${due_date_index}]}
  
  echo "due_date=${due_date}"

  # Check for vat returns.
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --due-date "${due_date}" --submit-vat-return --config ${config_file} --json
}

case $command in
  config)
    check_user_config
    config
    ;;
  create-user)
    check_user_config
    user
    ;;
  auth)
    check_user_config
    auth
    ;;
  test-fraud)
    check_user_config
    test_fraud
    ;;
  show-obligations)
    check_user_config
    show_obligations
    ;;
  show-open-obligations)
    check_user_config
    show_open_obligations
    ;;
  show-payments)
    check_user_config
    show_payments
    ;;
  show-liabilities)
    check_user_config
    show_liabilities
    ;;
  show-vat-return)
    check_user_config
    due_date_index=${2:-0}
    if [[ ! "${due_date_index}" == "0" ]] && [[ ! "${due_date_index}" == "1" ]]; then
        echo "ERROR: Parameter 1 must be 0 or 1"
        exit 1
    fi
    show_vat_return $due_date_index
    ;;
  show-account-summary)
    check_user_config
    due_date_index=${2:-0}
    if [[ ! "${due_date_index}" == "0" ]] && [[ ! "${due_date_index}" == "1" ]]; then
        echo "ERROR: Parameter 1 must be 0 or 1"
        exit 1
    fi
    show_account_summary $due_date_index
    ;;
  show-account-detail)
    check_user_config
    due_date_index=${2:-0}
    if [[ ! "${due_date_index}" == "0" ]] && [[ ! "${due_date_index}" == "1" ]]; then
        echo "ERROR: Parameter 1 must be 0 or 1"
        exit 1
    fi
    show_account_detail $due_date_index
    ;;
  submit-vat-return)
    check_user_config
    due_date_index=${2:-0}
    if [[ ! "${due_date_index}" == "0" ]] && [[ ! "${due_date_index}" == "1" ]]; then
        echo "ERROR: Parameter 1 must be 0 or 1"
        exit 1
    fi
    submit_vat_return $due_date_index
    ;;
  help)
    print_help
    ;;
esac