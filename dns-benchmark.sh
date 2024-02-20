#!/usr/bin/env zsh

CONFIG_FILE="config.yaml"

# Check for necessary commands
if ! command -v dig &> /dev/null; then
    echo "dig command could not be found"
    exit
fi

if ! command -v shyaml &> /dev/null; then
    echo "shyaml command could not be found. Try installing with 'pip install shyaml'."
    exit
fi

# Read the configuration from the YAML file
nameservers=("${(@f)$(shyaml get-values nameserver < "$CONFIG_FILE")}")
domains=("${(@f)$(shyaml get-values domain < "$CONFIG_FILE")}")

# Function to perform DNS query
perform_dns_query() {
    local nameserver=$1
    local domain=$2
    local output query_time

    if [[ $nameserver == "https://"* ]]; then
        # DoH query
        host_with_path=${nameserver#*://}  # Remove the protocol
        host=${host_with_path%%/*}  # Remove the path
        output=$(kdig @$host $domain +https +retry=0 2>&1)
    elif [[ $nameserver == "tls://"* ]]; then
        # DoT query
        host_with_path=${nameserver#*://}
        host=${host_with_path%%/*}
        output=$(kdig @$host $domain +tls +retry=0 2>&1)
    elif [[ $nameserver == "quic://"* ]]; then
        # DoQ query
        host_with_path=${nameserver#*://}
        host=${host_with_path%%/*}
        output=$(kdig @$host $domain +quic +retry=0 2>&1)
    else
        # Normal DNS query
        output=$(kdig @$nameserver $domain +retry=0 2>&1)
    fi

    # Get query time
    query_time=$(echo "$output" | awk '/From/{print $5}')
    echo "$query_time"
}

# Loop for each domain
for domain in "${domains[@]}"; do
    echo "----------------------------------------------------------------------"
    echo ">>Benchmark for $domain:<<"
    declare -A query_results

    # Perform DNS queries
    for nameserver in "${nameservers[@]}"; do
        # result=$(perform_dns_query "$nameserver" "$domain")
        # 在新的进程中查询
        result=$(perform_dns_query "$nameserver" "$domain" &)

        if [[ -z "$result" ]]; then
            result="TIMEOUT"
        else
            result=${result}ms
        fi

        query_results[$nameserver]=$result
    done

    # Print results
    for nameserver query_time in "${(@kv)query_results}"; do
        printf "%-60s %4s\n" "$nameserver" "${query_time}"
    done
done
echo "----------------------------------------------------------------------"
