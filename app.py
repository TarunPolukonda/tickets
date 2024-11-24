from flask import Flask,redirect,render_template,url_for,request,session,flash
import pymysql
from flask_session import Session
from key import secret_key
from stoken import token,dtoken
from cmail import sendmail
from otp import genotp
import base64,razorpay,json,ast
app=Flask(__name__)
app.config['SESSION_TYPE']='filesystem'
RAZORPAY_KEY_ID='rzp_test_c6m46TaGhi7qx3'
RAZORPAY_KEY_SECRET='fARQS1WX4v942Z4ayClkzUSZ'
client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))
Session(app)
mydb=pymysql.connect(host='localhost',user='root',password='root',db='bms')
@app.route("/")
def home():
    return render_template("index.html")
@app.route('/signin',methods=['GET','POST'])
def signin():
    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor()
        cursor.execute('select count(*) from user where email=%s',[email])
        email_count=cursor.fetchone()[0]
        if email_count==0:
            otp=genotp()
            data={'username':name,'email':email,'password':password,'otp':otp}
            subject='OTP Verification for Movie Ticket Booking App'
            body=f'Use this otp for verification {otp}'
            sendmail(to=email,subject=subject,body=body)
            flash('Otp send successfully')
            return redirect(url_for('verifyotp',data1=token(data)))
        elif email_count==1:
            flash('Email Already existed...')
            return redirect(url_for('login'))
        else:
            return 'something went wrong'
    return render_template('signin.html')
@app.route('/otp/<data1>',methods=['GET','POST'])
def verifyotp(data1):
    try:
        data1=dtoken(data=data1)
        print("data",data1)
    except Exception as e:
        print(e)
        return 'time out of opt'
    else:  
        if request.method=='POST':
            uotp=request.form['otp']
            if uotp==data1['otp']:
                cursor=mydb.cursor()
                cursor.execute('insert into user(name,email,password) values(%s,%s,%s)',[data1['name'],data1['email'],data1['password']])
                mydb.commit()
                cursor.close()
                flash('Registration successfull')
                return redirect(url_for('login'))
            else:
                return f'otp invalid pls check your mail.'
    finally:
        print('done')
    return render_template('otp.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('email'):
        return redirect(url_for('movies'))
    else:
        if request.method=='POST':
            email=request.form['email']
            password=request.form['password']
            try:
                cursor=mydb.cursor()
                cursor.execute('select email,password from user where email=%s',[email])
                data=cursor.fetchone()

                if password.encode('utf-8')==data[1]:
                    return redirect(url_for('movies'))
            except Exception as e:
                print(e)
                return "Invalid credentials"

    return render_template('login.html')

@app.route('/movies',methods=['GET','POST'])
def movies():
    
    if request.method=='POST':
        return redirect(url_for('theaters'))
    return render_template('movies.html')
@app.route('/theaters',methods=['GET','POST'])
def theaters():
    mname=request.args.get('mname')
    time=request.args.get('time')
    print("mname",mname,"time",time)
    if request.method=='POST':
        return redirect(url_for('seats',mname=mname,time=time))
    return render_template('theaters.html',mname=mname)

@app.route('/seats/<mname>/<time>', methods=['GET', 'POST'])
def seats(mname, time):
    # Retrieve 'count' and ensure `time` consistency between route and query parameters
    count = request.args.get('count', default=0, type=int)
    time_param = request.args.get('time', default=time)

    cursor = mydb.cursor()

    # Query booked seats for the specific movie and show time
    query = """
        SELECT seat 
        FROM tickets 
        WHERE mname = %s AND show_time = %s
    """
    cursor.execute(query, (mname, time_param))
    data = cursor.fetchall()

    # Parse and flatten the booked seats
    cleaned_data = [json.loads(item[0]) for item in data]
    booked_seats = [seat for sublist in cleaned_data for seat in ast.literal_eval(sublist)]

    print(f"Booked seats for {mname} at {time_param}: {booked_seats}")

    cursor.close()

    # Render the seat selection page with the booked seats
    return render_template(
        'seats.html',
        count=count,
        mname=mname,
        time=time_param,
        booked_seats=booked_seats
    )


@app.route('/pay/<name>/<int:price>/<int:count>/<time>', methods=['GET', 'POST'])
def pay(name, price, count, time):
    print(f"Accessing /pay route with name={name}, price={price}, count={count}, time={time}")

    try:
        # Get selected seats from query parameters
        seat_values = request.args.get('seats', '')
        seat_list = seat_values.split(',') if seat_values else []

        print(f"Selected seats: {seat_list}")

        if request.method == 'POST':
            amount = price * 100 * count  # Convert price to paise
            print(f"Creating Razorpay order for {amount} INR")

            # Create Razorpay order
            order = client.order.create({
                'amount': amount,
                'currency': 'INR',
                'payment_capture': '1'
            })

            print(f"Razorpay order created: {order}")
            return render_template('pay.html', order=order, seat_list=seat_list,name=name,time=time)

        return 'Invalid method', 400
    except Exception as e:
        print(f"Error: {e}")
        return str(e), 400


@app.route('/success/<name>/<time>',methods=['GET','POST'])
def success(name,time):
    if request.method=='POST':
        print("Time",time)
        print("succes mname",name)
        seat_list = request.form.get('seat_list')  # Retrieve seat_list from form
        seat_list = json.dumps(seat_list)  # Convert back to a list

    # Now you have seat_list as a list to work with
        print("seat_list",seat_list)

        try:
            cursor=mydb.cursor()
            cursor.execute('insert into tickets(mname,seat,show_time) values(%s,%s,%s)',[name,seat_list,time])
            mydb.commit()
            cursor.close()
            
            return render_template('orders.html',mname=name,seat_list=seat_list,time=time)
        except Exception as e:
            print(e)
            return "Error"

    
app.run(debug=True,use_reloader=True)