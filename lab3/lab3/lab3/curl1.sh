for i in `seq 1 5`; do
curl -d 'entry=s'${i} -X 'POST' 'http://10.1.0.1:8080/board'
done
for i in `seq 1 5`; do
curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.5:8080/board'
done
