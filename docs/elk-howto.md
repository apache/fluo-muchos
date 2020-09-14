Using the ELK Stack service with Fluo Muchos
--------------------------------------------------------------------

ELK is the acronym for three open source projects: Elasticsearch, Logstash, and Kibana. Elasticsearch is a search and 
analytics engine. Logstash is a server‑side data processing pipeline that ingests data from multiple sources 
simultaneously, transforms it, and then sends it to a "stash" like Elasticsearch. Kibana lets users visualize data with 
charts and graphs in [Elasticsearch](https://www.elastic.co/what-is/elk-stack). 

After the setup has completed, a pipeline will be created for Logstash and Filebeat. To view the dashboard visit the 
[Kibana](http://localhost:5601/app/kibana#/home) web page. 

For using Elasticsearch data: 

1. Connect to the Elasticsearch index. In the 'Index Pattern' field, enter * and click Next 
step. 
2. Select the 'Time Filter' field name from the dropdown. (Ex. @timestamp) Click Create index pattern.

On the menu on the left side corner, select Discover to view the incoming hits and query a specific subset within a selected 
timeframe. 

For examples on how to query in Kibana please visit the Elastico website [here](https://www.elastic.co/guide/en/beats/packetbeat/current/kibana-queries-filters.html) . 


