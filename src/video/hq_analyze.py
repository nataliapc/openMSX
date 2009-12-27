# $Id$

from hq import (
	Parser2x, Parser3x, Parser4x, getZoom, scaleWeights
	)
from hq_gen import (
	edges, expandQuadrant, genExpr2, genExpr3, genExpr4, simplifyWeights
	)

from collections import defaultdict
from itertools import izip

def normalizeWeights(pixelExpr):
	maxSum = max(
		sum(weights)
		for expr in pixelExpr
		for weights in expr
		)
	return [
		[ scaleWeights(weights, maxSum) for weights in expr ]
		for expr in pixelExpr
		]

def extractTopLeftWeights(weights):
	assert all(weights[n] == 0 for n in (2, 5, 6, 7, 8)), weights
	return weights[0 : 2] + weights[3 : 5]

def extractTopLeftQuadrant(pixelExpr):
	zoom = getZoom(pixelExpr)
	quadrantWidth = (zoom + 1) / 2
	quadrantMap = [
		qy * zoom + qx
		for qy in xrange(quadrantWidth)
		for qx in xrange(quadrantWidth)
		]
	for expr in [
		[ expr[subPixel] for subPixel in quadrantMap ]
		for expr in pixelExpr
		]:
		for weights in expr:
			for neighbour in (2, 5, 6, 7, 8):
				assert weights[neighbour] == 0, weights
	return [
		[ extractTopLeftWeights(expr[subPixel]) for subPixel in quadrantMap ]
		for expr in pixelExpr
		]

def convertExpr4to2(case, expr4):
	weights2 = [0] * 4
	for weights4 in expr4:
		for neighbour, weight in enumerate(scaleWeights(weights4, 256)):
			weights2[neighbour] += weight
	weights2 = simplifyWeights(weights2)
	if ((case >> 4) & 15) in (2, 6, 8, 12):
		assert sorted(weights2) == [0, 2, 7, 23]
		weightMap = { 0: 0, 2: 1, 7: 1, 23: 2 }
	elif ((case >> 4) & 15) in (0, 1, 4, 5):
		assert sorted(weights2) == [0, 3, 3, 10]
		weightMap = { 0: 0, 3: 1, 10: 2 }
	else:
		weightMap = None
	if weightMap:
		weights2 = tuple(weightMap[weight] for weight in weights2)
	return [weights2]

def convert4to2(topLeftQuadrant4):
	return [
		convertExpr4to2(case, expr4)
		for case, expr4 in enumerate(topLeftQuadrant4)
		]

def analyzeCaseFunction(caseToWeights):
	weightsToCase = defaultdict(set)
	for case, weights in enumerate(caseToWeights):
		weightsToCase[weights].add(case)
	for weights in sorted(weightsToCase.iterkeys()):
		cases = weightsToCase[weights]
		partitions = set(
			tuple((case >> edgeNum) & 1 for edgeNum in xrange(11, -1, -1))
			for case in cases
			)
		# Repeatedly merge partitions until we have a minimal set.
		for edgeNum in xrange(12):
			changed = True
			while changed:
				changed = False
				for part in list(partitions):
					if part not in partitions:
						continue
					if part[edgeNum] < 2:
						pre = part[ : edgeNum]
						post = part[edgeNum + 1 : ]
						dual = pre + (part[edgeNum] ^ 1,) + post
						if dual in partitions:
							partitions.remove(part)
							partitions.remove(dual)
							partitions.add(pre + (2,) + post)
							changed = True
		yield weights, [
			''.join('01x'[bit] for bit in partition)
			for partition in sorted(partitions)
			]

# Various analysis:

def findRelevantEdges():
	for parserClass in (Parser2x, Parser3x, Parser4x):
		parser = parserClass()
		quadrant = normalizeWeights(extractTopLeftQuadrant(parser.pixelExpr))
		quadrantWidth = (parser.zoom + 1) / 2
		assert quadrantWidth ** 2 == len(quadrant[0])
		subPixelOutput = [[] for _ in xrange(quadrantWidth * 10)]
		for subPixel in xrange(quadrantWidth ** 2):
			neighbourOutput = [[] for _ in xrange(8)]
			for neighbour in xrange(4):
				relevant = [
					edgeNum
					for edgeNum in xrange(12)
					if any(
						quadrant[case][subPixel][neighbour] !=
							quadrant[case ^ (1 << edgeNum)][subPixel][neighbour]
						for case in xrange(len(quadrant))
						)
					]
				zero = len(relevant) == 0 and all(
					quadrant[case][subPixel][neighbour] == 0
					for case in xrange(len(quadrant))
					)
				center = ('.' if zero else str(neighbour))
				for rowNum, row in enumerate(formatEdges(relevant)):
					if rowNum == 1:
						assert row[1] == 'o'
						row = row[0] + center + row[2]
					neighbourOutput[(neighbour / 2) * 4 + rowNum].append(row)
				neighbourOutput[(neighbour / 2) * 4 + 3].append('   ')
			for lineNum, line in enumerate(neighbourOutput):
				lineOutput = '  %s  |' % '  '.join(line)
				subPixelOutput[
					(subPixel / quadrantWidth) * 10 + lineNum + 1
					].append(lineOutput)
				if lineNum == 7:
					subPixelOutput[(subPixel / quadrantWidth) * 10].append(
						lineOutput
						)
					subPixelOutput[(subPixel / quadrantWidth) * 10 + 9].append(
						'%ss%d' % ('-' * (len(lineOutput) - 2), subPixel)
						)
		print 'Relevant edges for zoom %d:' % parser.zoom
		print
		for line in subPixelOutput:
			print '  %s' % ''.join(line)
		print

# Visualization:

def formatEdges(edgeNums):
	cells = ['.' for _ in xrange(9)]
	cells[4] = 'o'
	def combine(index, ch):
		old = cells[index]
		if old == '.':
			cells[index] = ch
		elif (old == '/' and ch == '\\') or (old == '\\' and ch == '/'):
			cells[index] = 'X'
		else:
			assert False, (index, old, ch)
	for edgeNum in edgeNums:
		edge = edges[edgeNum]
		if 4 in edge:
			other = sum(edge) - 4
			combine(other, '\\|/-'[other if other < 4 else 8 - other])
		else:
			assert edge in ((1, 5), (5, 7), (3, 7), (1, 3))
			x = 0 if 3 in edge else 2
			y = 0 if 1 in edge else 2
			combine(y * 3 + x, '/' if x == y else '\\')
	for y in xrange(3):
		yield ''.join(cells[y * 3 : (y + 1) * 3])

def formatWeights(weights):
	return ' '.join('%3d' % weight for weight in weights)

def comparePixelExpr(pixelExpr1, pixelExpr2):
	zoom = getZoom(pixelExpr1)
	assert zoom == getZoom(pixelExpr2)
	mismatchCount = 0
	for case, (expr1, expr2) in enumerate(izip(pixelExpr1, pixelExpr2)):
		if expr1 != expr2:
			binStr = bin(case)[2 : ].zfill(12)
			print 'case: %d (%s)' % (
				case,
				' '.join(binStr[i : i + 4] for i in range(0, 12, 4))
				)
			for sy in xrange(zoom):
				matrices = []
				for sx in xrange(zoom):
					subPixel = sy * zoom + sx
					subExpr1 = expr1[subPixel]
					subExpr2 = expr2[subPixel]
					rows = []
					for ny in xrange(3):
						rows.append('%s   %s %s' % (
							formatWeights(subExpr1[ny * 3 : (ny + 1) * 3]),
							'.' if subExpr1 == subExpr2 else '!',
							formatWeights(subExpr2[ny * 3 : (ny + 1) * 3])
							))
					matrices.append(rows)
				for ny in xrange(3):
					print '  %s' % '       '.join(
						matrices[sx][ny]
						for sx in xrange(zoom)
						)
				print
			mismatchCount += 1
	print 'Number of mismatches: %d' % mismatchCount

# Sanity checks:

def checkQuadrants():
	for parserClass in (Parser2x, Parser3x, Parser4x):
		parser = parserClass()
		topLeftQuadrant = extractTopLeftQuadrant(parser.pixelExpr)
		expanded = expandQuadrant(topLeftQuadrant, parser.zoom)
		comparePixelExpr(expanded, parser.pixelExpr)

def checkConvert4to2():
	parser4 = Parser4x()
	topLeftQuadrant4 = extractTopLeftQuadrant(parser4.pixelExpr)
	topLeftQuadrant2 = convert4to2(topLeftQuadrant4)
	pixelExpr2 = expandQuadrant(topLeftQuadrant2, 2)

	parser2 = Parser2x()
	comparePixelExpr(pixelExpr2, parser2.pixelExpr)

def checkGen2():
	pixelExpr2 = expandQuadrant(genExpr2(), 2)
	comparePixelExpr(pixelExpr2, Parser2x().pixelExpr)

def checkGen3():
	pixelExpr3 = expandQuadrant(genExpr3(), 3)
	comparePixelExpr(pixelExpr3, Parser3x().pixelExpr)

def checkGen4():
	pixelExpr4 = expandQuadrant(genExpr4(), 4)
	comparePixelExpr(pixelExpr4, Parser4x().pixelExpr)

# Main:

if __name__ == '__main__':
	findRelevantEdges()
	checkQuadrants()
	checkConvert4to2()
	checkGen2()
	checkGen3()
	checkGen4()