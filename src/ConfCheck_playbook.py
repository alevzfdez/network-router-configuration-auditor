import os, coloredlogs, logging, sys, time
import argparse, requests, csv, re, json


######################################################################################
# 0. Set-up environment
######################################################################################

# Set arguments to be parsed
parser = argparse.ArgumentParser(description='''Configuration Check playbook v1.0''')
parser.add_argument('--debug', '-d', dest='debug', choices=['on', 'off'], default='off', 
                    help='Turn debugging mode on-off')
parser.add_argument('--nodes', '-n', dest='nodes',
                    help='Nodes list in CSV. Will process checks under list nodes')
parser.add_argument('--checks', '-c', dest='checks',
                    help='Configuration checks JSON file as input')

# Check & set args
args = parser.parse_args()

# Debug Set
def str_to_bool(s):
    if s == 'on':
         return False
    elif s == 'off':
         return True
    else:
         raise ValueError
    return

# Set debug environment
def logging_set(args):
    handler = logging.StreamHandler()
    handler.addFilter(coloredlogs.HostNameFilter())
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s'))
    logger=logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.disabled=str_to_bool(args.debug)
    logging.debug(args)
    coloredlogs.install(level='DEBUG', logger=logger)
    return

######################################################################################
# 1. Request latest commited config
#   https://360.mm-red.net/admin/inventory/oxidized/node/config/AX4024-LER01/5171
#   https://360.mm-red.net/admin/inventory/oxidized/node/config/<node_code>/<node_id>
######################################################################################
def get_conf(node_info):
    url_conf = 'https://ispdomain.com/admin/inventory/oxidized/node/config/'+node_info[2]+'/'+node_info[0]
    https_headers = {'PHPSESSID':'key',
        'REMEMBERME':'cookie'
        }
    try:
        node_conf = requests.get(url_conf, cookies=https_headers)
        """ time.sleep(1) """
    except requests.exceptions.HTTPError as e:
        # Whoops it wasn't a 200
        logging.debug( "[Error: " + str(e))
        return "Error_get"
    
    return str(node_conf.text).replace('<br />', '')

######################################################################################
# 2. Parse retrived configuration and search for required matches
######################################################################################
def parse_conf(node_info, node_conf_arr):
    node_info_filtered = str(';'.join(node_info[:6]))

    # Load JSON checks to be done
    with open(args.checks, 'r') as json_file: 
        find_conf = json.load(json_file)

    # Run configuration checker algorithm
    node_conf_parsed = []
    for item_index in range(len(list(find_conf.values()))):
        item_search_key = list(find_conf.keys())[item_index]
        item_search_condition = list(find_conf.values())[item_index][0]
        item_search_value = list(find_conf.values())[item_index][1].split('\n')
        
        logging.debug('[Search_token]\t\t'+str(item_search_key))

        if len(item_search_value) == 1:
            if not item_search_value[0]:
                node_conf_parsed.append(str(node_info_filtered)+';'+'Not_Found'+';'+str(0)+';'+str(item_search_key)+';'+str(item_search_condition)+';'+'-')
                logging.debug('[Not_Found_Empty]\t\t' + str(item_search_key))
            elif item_search_value[0] in node_conf_arr:
                node_conf_parsed.append(str(node_info_filtered)+';'+'Found'+';'+str(node_conf_arr.index(item_search_value[0])-24)+';'+str(item_search_key)+';'+str(item_search_condition)+';'+str(item_search_value[0]))
                logging.debug('[Found]\t\t' + str(item_search_key))
            else:
                node_conf_parsed.append(str(node_info_filtered)+';'+'Not_Found'+';'+str(0)+';'+str(item_search_key)+';'+str(item_search_condition)+';'+str(item_search_value[0]))
                logging.debug('[Not_Found]\t\t' + str(item_search_key))
        elif len(item_search_value) > 1:
            node_conf_parsed.append(str(node_info_filtered)+';'+'Not_Found'+';0;-;-;'+'multi line search not supported')
            logging.debug('[Not_Found]\t\t' + ';' + 'Not supported')
    
    return node_conf_parsed

######################################################################################
# 3. Export results to csv file
######################################################################################
def export_parsed_results(node_conf_parsed, header=False):
    parsed_header = ['ID', 'NAME', 'CODE', 'DESCRIPTION', 'VENDOR', 'MODEL', 'RESULT', 'MATCHED LINE', 'SEARCH KEY', 'GOOD_BAD', 'DETAILS']
    t = time.localtime()
    timestamp = time.strftime('%b-%d-%Y_%H%M', t)
    csvfile = timestamp + '-out.csv'
    
    with open(csvfile, 'a') as output:
        writer = csv.writer(output, lineterminator='\n')
        if header is True:
            writer.writerow([';'.join(parsed_header)])
            return
        else:
            for search_result in node_conf_parsed:
                writer.writerow([search_result])


if __name__ == "__main__":
    logging_set(args)
    node_info_list = []

    with open(args.nodes, 'r') as node:
        node_list = node.readlines()
        for node_line in node_list:
            node_info_list.append(node_line.split(';'))

    export_parsed_results([], True)
    for node_info in node_info_list:
        node_conf = get_conf(node_info)
        logging.debug(node_info[:6])
        if node_conf == "Error_get" or (node_info[4] != 'Juniper' and node_info[4] != 'Huawei' and node_info[4] != 'Nokia'):
            pass
        else:
            node_conf_arr = list(map(str.strip, node_conf.splitlines()))
            node_conf_parsed = parse_conf(node_info, node_conf_arr)
            export_parsed_results(node_conf_parsed)
    
    logging.debug('[Finised -- OK]')
