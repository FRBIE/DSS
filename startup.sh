#!/bin/sh
# 等待数据库就绪（最多尝试 30 次，每次等待 2 秒）
echo "等待数据库连接..."
for i in {1..30}; do
  poetry run python -c "
  import MySQLdb
  try:
      conn = MySQLdb.connect(
          host='db',
          user='mediCore',
          passwd='bWVkaUNvcmU=',
          db='medical_data'
      )
      conn.close()
      print('数据库已就绪！')
      exit(0)
  except MySQLdb.OperationalError:
      print(f'尝试连接数据库（第 {i} 次）...')
      exit(1)
  " && break || sleep 2
done  # 这里缺少 done 关键字来结束 for 循环
# 执行迁移并启动服务器
poetry run python manage.py makemigrations --noinput
poetry run python manage.py migrate --noinput
poetry run python manage.py runserver 0.0.0.0:8000