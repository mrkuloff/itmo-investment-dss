~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	capital budgeting problem instances
		by Rong Qu
		May 2009
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This package contains 2 * 10 files of capial budgeting problems with single
time period. They are produced based on the Excel tool by Winston W.L. and
Albright S.C. Practical Management Science, South-Western College Pub, 2007.

The problem to be solved is:
 Max  sum{j=1,...,n} p(j)x(j)
 st   sum{j=1,...,n} r(j)x(j) <= b
                     x(j)=0 or 1

The format of each file is:

number of projects	total cost required

the coefficients p(j); j=1,...,n
the coefficients r(j); j=1,...,n

the best solution known	the best NPV	the cost of best solution

dependent constraint (-1 if not exist)

exclusive constraint (-1 if not exist)

contingency constraint

ratios of NPV/cost for each project