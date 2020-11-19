for j in `seq 1 10`; do
for i in `seq 1 40`; do
curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.'${j}':8080/board'
done
done
