import datetime
import numpy as np
import matplotlib.colors as colors
import matplotlib.finance as finance
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import csv
import time

def moving_average(x, n, type='simple'):
    """
    compute an n period moving average.

    type is 'simple' | 'exponential'

	x = prices

    """
    x = np.asarray(x)
    if type == 'simple':
        weights = np.ones(n)
    else:
        weights = np.exp(np.linspace(-1., 0., n))

    weights /= weights.sum()

    a = np.convolve(x, weights, mode='full')[:len(x)]
    a[:n] = a[n]
    return a


def relative_strength(prices, n=14):
    """
    compute the n period relative strength indicator
    http://stockcharts.com/school/doku.php?id=chart_school:glossary_r#relativestrengthindex
    http://www.investopedia.com/terms/r/rsi.asp
    """

    deltas = np.diff(prices)
    seed = deltas[:n+1]
    up = seed[seed >= 0].sum()/n
    down = -seed[seed < 0].sum()/n
    rs = up/down
    rsi = np.zeros_like(prices)
    rsi[:n] = 100. - 100./(1. + rs)

    for i in range(n, len(prices)):
        delta = deltas[i - 1]  # cause the diff is 1 shorter

        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up*(n - 1) + upval)/n
        down = (down*(n - 1) + downval)/n

        rs = up/down
        rsi[i] = 100. - 100./(1. + rs)

    return rsi


def moving_average_convergence(x, nslow=26, nfast=12):
    """
    compute the MACD (Moving Average Convergence/Divergence) using a fast and slow exponential moving avg'
    return value is emaslow, emafast, macd which are len(x) arrays
    """
    emaslow = moving_average(x, nslow, type='exponential')
    emafast = moving_average(x, nfast, type='exponential')
    return emaslow, emafast, emafast - emaslow

def evaluate(stock, numdays = 30):
	'''
	Evaluate a certian stock passed in as a string
	Stock: The stock to look at.
	numdays: the number of days to compare against 
	'''
	print("==========")
	print("|| " + stock + " ||")
	print("==========")
	fh = finance.fetch_historical_yahoo(stock, startdate, enddate)
	r = mlab.csv2rec(fh)
	fh.close()
	r.sort()

	prices = r.adj_close
	# Over 70: More over 70's = over bought
	# Under 30: More over 30's = over sold
	overbought = False
	oversold = False
	over = 0
	under = 0
	rsi = relative_strength(prices)
	# Itterate over the past numdays
	for x in range(rsi.__len__() - numdays, rsi.__len__()):
		# Detect positive slope crossing overbought line
		if rsi[x] > 70 and rsi[x - 1] < 70: 
			over+= 1
		# detect negative slope crossing oversold line
		elif rsi[x] < 30 and rsi[x-1] > 30:
			under+= 1
	if all(rsi[rsi.__len__()-3:] > 70):
		overbought = True
	elif all(rsi[rsi.__len__()-3:] < 30):
		oversold = True

	if overbought or oversold:
		print(stock + " is currently " + ("over bought" if overbought else "over sold"))

	print("Positive slope crosses across 70: " + over.__str__())
	print("Negative slope crosses across 30: " + under.__str__());
	#print("RSI: \n" + str(rsi[rsi.__len__() - numdays:rsi.__len__()]))

	ma20 = moving_average(prices, 20, type='simple')
	ma100 = moving_average(prices, 100, type='simple')

	volume = (r.close*r.volume)/1e6  # dollar volume in millions
	vmax = volume.max()

	nslow = 26
	nfast = 12
	nema = 9
	emaslow, emafast, macd = moving_average_convergence(prices, nslow=nslow, nfast=nfast)
	ema9 = moving_average(macd, nema, type='exponential') # creating the signal line
	# macd should by the ema26 - ema12, we compare the sinal line to this. a positive slope cross signals a rise in price, we should
	# buy while we can. a negative slope cross signals a price decline, we should sell while we can.
	# Grab the last 30 days:
	sigline = ema9[ema9.__len__() - numdays: ema9.__len__()]
	sigline = [x+10 for x in sigline] # positive biasing all values, makes my buy or sell trick less sketchy
	compline = macd[macd.__len__() - numdays: macd.__len__()]
	compline = [x+10 for x in compline] # positive biasing all values, makes my buy or sell trick less sketchy
	buyorsell = np.subtract(sigline, compline)
	slopesign = 0
	buy = False
	sell = False
	for x in range(numdays - 1, 0, -1):
		if all(buyorsell[x:numdays -1] > 0) or all(buyorsell[x:numdays -1] < 0):
			continue
		else:
			if buyorsell[x] > 0:
				print("Signal to sell " + str(numdays - x) + " days ago")
				sell = True
				selllist.append(stock)
			else:
				print("Signal to buy " + str(numdays - x) + " days ago")
				buy = True
				buylist.append(stock)
			break
	if buy or sell:
		print("Suggested action on: " + stock + " is to " + ("buy" if buy else ("sell" if sell  else "take no action")))

# More or less what I am using as global variables

startdate = datetime.date(2014, 1, 1)
today = enddate = datetime.date.today()
highprice = 100.0
lowprice = 10.0
# the amount of time in the past we want to really look at for buying, the rest is just
# about getting more info on the stock.
numdays = 30

# Stocks I am 'currently' interested in.
stocks = ['']
# List of all the finance info on teh stocks
stockinfo = ['']
buylist = ['']
selllist = ['']

''' Grabbing all of the companies from the NASDAQ stock exchange '''
with open('companylist.csv') as csvfile:
	freader = csv.reader(csvfile, delimiter=',')
	for line in freader:
		# Get rid of the header line, as well as any stocks with no prices...
		if line[2] == "LastSale" or line[2] == "n/a":
			continue
		#Only getting companies we can afford.....
		elif float(line[2]) < highprice and float(line[2]) > lowprice:
			stocks.append(line[0])


''' Plan:
	-Go through stock by stock, Fet out each one, (check if the price is say between $10-$100 or something
	-On stocks that fit this bill, we want to run our analysis
	-find out if the company is on an up swing or down swing, and print to sell or buy IF
		-in the last month the RSI shows that we should consider dealing with this stock.

 '''

'''Where the Magic happens!'''
start_time = time.time()
for ticker in stocks:
	if ticker != "":
		#try:
		evaluate(ticker, numdays)
		#except IndexError:
		#	print(ticker + " stock is to young / not enough data available, ignore suggestions about stock.")
		#except Exception:
		#	print("Error getting " + ticker + " data, ignore suggestions about stock")
end_time = time.time()
uptime = end_time - start_time
print("Stock analysis done in: " + datetime.timedelta(seconds=int(uptime)).__str__())
print("Buy these stocks: ")
print(buylist)
print("Sell these stocks: ")
print(selllist)
