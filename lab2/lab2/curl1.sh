for i in `seq 1 5`; do
curl -d 'entry=s'${i} -X 'POST' 'http://10.1.0.10:8080/board'
done
