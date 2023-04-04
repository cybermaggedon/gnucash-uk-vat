#!/bin/bash

# This should work on linux and Windows Git Bash

# This uses the HMRC test sandbox
default_config_file=config.json

# Indexed test data. Stored in gnuCash accounts and MTD test system.
start_date_list=("2017-01-01" "2017-04-01" "2017-01-01" "2017-01-01")
end_date_list=(  "2017-03-31" "2017-06-30" "2017-12-31" "2017-12-31")
due_date_list=(  "2017-05-07" "2017-08-07" "2017-05-07" "2017-08-07")
# Select the MTD data to test against
gov_test_scenario_list=( "QUARTERLY_ONE_MET", "QUARTERLY_ONE_MET", "QUARTERLY_ONE_MET", "QUARTERLY_ONE_MET" )

# NOTE: This needs updating each time a command is added
valid_commands=( 
    config 
    create-user 
    auth 
    test-fraud 
    show-obligations 
    show-open-obligations 
    show-payments 
    show-liabilities 
    submit-vat-return 
    show-vat-return 
    show-account-summary 
    show-account-detail 
    help 
)


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
       $HOME/${private_config_file}
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

# Create Config File
The config.json file can be created or updated using the command:
    '$0 config <config_file>'
This will create a local config file using the defaults from config_file and config_private_file.

NOTE#1: The name of the config file is stored in the file .config_file and will be loaded by all other commands
NOTE#2: The 'identity.vrn' field can't be populated until there is an 
      application.client-[id|secret]
      See 'Create HMRC User' section below.

# Create Test User
When using the test (sandbox) profile, you will need to create a test user (Don't use your HMRC production credentials!)
    '$0 user'
This creates a user in the MTD system and downloads the users details into user.json
It also updates the config fiel with the new VRN.
NOTE: This command assumes the application associated with the client-id in 
          ${config_file}
      has been configured to access the 'Create Test User' endpoint 
      in 'API Subscriptions' when viewin application details from here:
      https://developer.service.hmrc.gov.uk/developer/applications

# Update ${config_file} with VRN
After updating the user.json file, update the config file to use the new test VRN.
    '$0 config <config_file>'

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
NOTE #2: This command assumes the application associated with the client-id in config_file
         has been configured to access the 'Test Fraud Prevention Headers' endpoint 
         in 'API Subscriptions' when viewin application details from here:
         https://developer.service.hmrc.gov.uk/developer/applications

# show-obligations
Show all obligations in MTD for the test year
    '$0 show-obligations'
This should show both Finished and Open VAT obligations.

# show-open-obligations
Show all open obligations in MTD for the test year
    '$0 show-open-obligations'
This should only show Open VAT obligations.

# show-account-summary
Show GnuCash account summary for a particular due_date
    '$0 show-account-summary [0|1|2|3]'
This will report the account summary for the Obligation matching the due_date_index.

# show-account-detail
Show GnuCash account details for a particular due_date
    '$0 show-account-detail [0|1|2|3]'
This will report the account details for the Obligation matching the due_date_index.

# show-liabilities
Show VAT liabilities for start and end dates
    '$0 show-liabilities'
This will report the current liabilities matching the due_date_index.

# show-payments
Show VAT payments for start and end dates
    '$0 show-payments'
This will report the VAT payments matching the due_date_index.

# show-vat-return
Show VAT return for due dates
    '$0 show-vat-return [0|1|2|3]'
This will report the VAT returns matching the due_date_index.

# submit-vat-return
Show VAT payments for due dates
    '$0 submit-vat-return [0|1|2|3]'
This will submit VAT return matching the due_date_index.

HEREDOC
)


# Check for a json configuration file in $HOME with user specific configuration 
check_private_config() {
  pushd ${HOME} 2>&1 > /dev/null
  if [[ ! -f ${private_config_file} ]]; then
      #  If missing, create the private_config_file
      if [[ -f $(dirname $(which python))/scripts/gnucash-uk-vat ]]; then
        # Create a private_config_file
        python $(dirname $(which python))/scripts/gnucash-uk-vat --init-config --config ${private_config_file}
        return_code=$?
        if [[ $return_code -ne 0 ]]; then
            echo "[ERROR] Failed to create users static gnucash config file: ${private_config_file}"
            exit 1
        else
            echo "Now update the 'accounts', 'application' and 'identy' stanzas for the environment being tested against"
            echo "These can be used to populate config files with fields that contain personal or sensitive infomation."
            echo "NOTE: Fields missing from the private user config file will be ignored, leaving the existing config value in-place."
            echo "Once configured to your requirements, re-run the 'config' command and these fields will update the config file."
        fi
      else
        echo "ERROR: Missing python script '$(dirname $(which python))/scripts/gnucash-uk-vat'. Run the setup"
      fi
      popd 2>&1 > /dev/null
      # Always stop the script here. Check logs for error or do manual changes to the configuration files.
      exit 1
  fi
  popd 2>&1 > /dev/null
}

print_help() {
  echo "$help_string"
}

config() {
  echo "Configuring gnucash-uk-vat using ${config_file}..."
  python $(dirname $(which python))/scripts/gnucash-uk-vat --init-config --config ${config_file}
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
  python -u test-fraud-api --config  ${config_file}
}

show_open_obligations() {
  echo "Test for Open Obligations against MTD website..."
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --show-open-obligations --config ${config_file} --json
}

show_obligations() {
  # Show VAT Obligations against MTD website...
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

set_date_variables() {

  data_index=$1

  if [[ ! -z "${data_index}" ]]; then
    echo "Get test dates from local data using index ${data_index}"
    start_date=${start_date_list[${data_index}]}
    end_date=${end_date_list[${data_index}]}
    due_date=${due_date_list[${data_index}]}
  else
    echo "Get VAT submission dates from config file: ${config_file}"
    if command -v jq &> /dev/null; then
      due_date=$( cat ${config_file} | jq -r '.dates?.due' )
      start_date=$( cat ${config_file} | jq -r '.dates?.start' )
      end_date=$( cat ${config_file} | jq -r '.dates?.end' )
    else
      echo "Missing tool. Please install 'jq' and try again"
      exit 1
    fi
  fi
  
}

show_vat_return() {
  echo "Show previous Vat Return against MTD website..."

  data_index=$1
  set_date_variables "${data_index}"
  echo "    start_date=${start_date}"
  echo "    end_date=${end_date}"
  echo "    due_date=${due_date}"

  # Check for vat returns.
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --due-date "${due_date}" --start "${start_date}"  --end "${end_date}" --show-vat-return --config ${config_file} --json
}

show_account_summary() {
  echo "Show GnuCash account summary against MTD website..."

  data_index=$1
  set_date_variables "${data_index}"
  echo "    due_date=${due_date}"

  # Check for vat returns.
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --due-date "${due_date}" --show-account-summary --config ${config_file} --json
}

show_account_detail() {
  echo "Show GnuCash account details against MTD website..."

  data_index=$1
  set_date_variables "${data_index}"
  echo "    due_date=${due_date}"

  # Check for vat returns.
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --due-date "${due_date}" --show-account-detail --config ${config_file} --json
}

submit_vat_return() {
  echo "Submit Vat Return against MTD website..."

  data_index=$1
  set_date_variables "${data_index}"
  echo "    due_date=${due_date}"

  # Check for vat returns.
  python -u $(dirname $(which python))/scripts/gnucash-uk-vat --due-date "${due_date}" --submit-vat-return --config ${config_file} --json
}

# Use the default_config_file name for all commands. 
# NOTE: Can only be overidden by 'config' command.
config_file=${default_config_file}


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

case $command in
  config)
    # Specifiies the config file to copy to default_config_file
    config_file=$2
    
    if [[ -z "$config_file" ]]; then
       echo "Invalid config_file: EMPTY_VARIABLE"
       exit 1
    fi

    private_config_file="${HOME}/.${config_file}"
    check_private_config
    config
    ;;
  create-user)
    user
    echo "IMPORTANT ADDITIONAL STEPS:"
    echo "    1. Run 'config' to incorporate the VRN from the new MTD test user"
    echo "    2. Run 'auth' to create authenticate token for new MTD test user"
    ;;
  auth)
    auth
    ;;
  test-fraud)
    test_fraud
    ;;
  show-obligations)
    show_obligations
    ;;
  show-open-obligations)
    show_open_obligations
    ;;
  show-payments)
    show_payments
    ;;
  show-liabilities)
    show_liabilities
    ;;
  show-vat-return)
    due_date_index=$2
    if [[ ! -z "${due_date_index}" ]] && [[ ! ${due_date_index} =~ [0-3] ]]; then
        echo "ERROR: If present, parameter #1 must be a single digit from 0 to 3"
        exit 1
    fi
    show_vat_return $due_date_index
    ;;
  show-account-summary)
    due_date_index=$2
    if [[ ! -z "${due_date_index}" ]] && [[ ! ${due_date_index} =~ [0-3] ]]; then
        echo "ERROR: If present, parameter #1 must be a single digit from 0 to 3"
        exit 1
    fi
    show_account_summary $due_date_index
    ;;
  show-account-detail)
    due_date_index=$2
    if [[ ! -z "${due_date_index}" ]] && [[ ! ${due_date_index} =~ [0-3] ]]; then
        echo "ERROR: If present, parameter #1 must be a single digit from 0 to 3"
        exit 1
    fi
    show_account_detail $due_date_index
    ;;
  submit-vat-return)
    due_date_index=$2
    if [[ ! -z "${due_date_index}" ]] && [[ ! ${due_date_index} =~ [0-3] ]]; then
        echo "ERROR: If present, parameter #1 must be a single digit from 0 to 3"
        exit 1
    fi
    submit_vat_return $due_date_index
    ;;
  help)
    print_help
    ;;
esac