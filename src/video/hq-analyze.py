# $Id$

from hq import (
	Parser2x, Parser3x, Parser4x,
	edges, getZoom, permuteCase, scaleWeights, simplifyWeights
	)

from collections import defaultdict
from itertools import izip

def computeCasePermutation(neighbourPermutation):
	return tuple(
		edges.index(tuple(sorted(
			(neighbourPermutation[n1], neighbourPermutation[n2])
			)))
		for n1, n2 in edges
		)

def permute(seq, permutation):
	seq = tuple(seq)
	assert len(seq) == len(permutation)
	return tuple(seq[index] for index in permutation)

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

def expandTopLeftWeights(weights):
	return weights[0 : 2] + (0, ) + weights[2 : 4] + (0, 0, 0, 0)

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

def expandQuadrant(topLeftQuadrant, zoom):
	quadrantWidth = (zoom + 1) / 2
	assert quadrantWidth ** 2 == len(topLeftQuadrant[0])
	mirrorMap = [None] * (zoom ** 2)
	permId = (0, 1, 2, 3, 4, 5, 6, 7, 8)
	permLR = (2, 1, 0, 5, 4, 3, 8, 7, 6)
	permTB = (6, 7, 8, 3, 4, 5, 0, 1, 2)
	for quadrantIndex in xrange(quadrantWidth ** 2):
		qy, qx = divmod(quadrantIndex, quadrantWidth)
		for ty, py in ((zoom - qy - 1, permTB), (qy, permId)):
			for tx, px in ((zoom - qx - 1, permLR), (qx, permId)):
				nperm = permute(px, py)
				cperm = computeCasePermutation(nperm)
				mirrorMap[ty * zoom + tx] = (quadrantIndex, cperm, nperm)
	return [
		[	permute(
				expandTopLeftWeights(
					topLeftQuadrant[permuteCase(case, cperm)][quadrantIndex]
					),
				nperm
				)
			for quadrantIndex, cperm, nperm in mirrorMap
			]
		for case in xrange(len(topLeftQuadrant))
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

def computeZ2S0W0(case):
	if (case & 0xFF8) in (
		0x0A0, 0x1A0, 0x2A0, 0x3A0, 0x4A0, 0x5A0, 0x7A0,
		0x8A0, 0x9A0, 0xAA0, 0xBA0, 0xCA0, 0xDA0, 0xEA0,
		0x1A8, 0x4A8,
		0x0E0, 0x2E0, 0x4E0, 0x5E0,0x8E0, 0x9E0, 0xAE0, 0xCE0
		):
		return 0
	elif (case & 0x0B0) == 0:
		return 0
	elif (case & 0x010) == 0x010:
		return 0
	else:
		return 4

def computeZ2S0W1(case):
	if (case & 0xFF8) in (
		0x2A0, 0xAA0, 0x2B0, 0xAB0, 0xBB0, 0xCF0, 0x0E0, 0x8E0, 0x0F0, 0x8F0
		):
		return 6
	elif (case & 0x3FC) in (0x1D0, 0x1D8, 0x1F0, 0x1F4):
		return 4
	elif (case & 0x0B4) in (0x000, 0x010, 0x080, 0x004, 0x014, 0x084, 0x094):
		return 4
	elif (case & 0xFF1) in (0x130, 0x170, 0x330, 0x370, 0x770):
		return 4
	elif (case & 0xFF4) in (
		0x0D0, 0x2D0, 0x3D0, 0x8D0, 0xAD0, 0xBD0, 0xCD0, 0xED0, 0xFD0,
		0x090, 0x190, 0x290, 0x390, 0x590, 0x790,
		0x890, 0x990, 0xA90, 0xB90, 0xC90, 0xD90, 0xE90, 0xF90
		):
		return 4
	elif (case & 0xFF8) in (
		0x0A0, 0x1A0, 0x4A0, 0x8A0, 
		0x0B0, 0x1B0, 0x3B0, 0x4B0, 0x5B0, 0x6B0, 0x7B0,
		0x8B0, 0x9B0, 0xCB0, 0xDB0, 0xEB0, 0xFB0,
		0x4F0
		):
		return 4
	elif (case & 0xFF8) in (
		0x3A0, 0x5A0, 0x7A0, 0x9A0, 0xBA0, 0xCA0, 0xDA0, 0xEA0,
		0x2E0, 0x4E0, 0x5E0, 0x9E0, 0xAE0, 0xCE0
		):
		return 2
	elif (case & 0xFF4) in (0x490, 0x4D0, 0x690, 0x6D0, 0x7D0):
		return 2
	elif (case & 0x2F8) == 0x2F0:
		return 1
	else:
		return 0

def genExpr2():
	quadrant = [
		[ None ]
		for case in xrange(1 << 12)
		]
	casePerm = computeCasePermutation((0, 3, 6, 1, 4, 7, 2, 5, 8))

	for case in xrange(1 << 12):
		w0 = computeZ2S0W0(case)
		w1 = computeZ2S0W1(case)
		w2 = computeZ2S0W1(permuteCase(case, casePerm))
		quadrant[case][0] = simplifyWeights((w0, w1, w2, 16 - w0 - w1 - w2))

	return quadrant


def computeZ3S0W0(case):
	if (case & 0xFF8) in (0x1A8, 0x4A8, 0x5E0, 0x7A0, 0x9E0, 0xEA0):
		return 0
	elif (case & 0x7F8) in (
		0x0A0, 0x0E0, 0x1A0, 0x2A0, 0x2E0, 0x3A0, 0x4A0, 0x4E0, 0x5A0
		):
		return 0
	elif (case & 0x0B0) == 0x000:
		return 0
	elif (case & 0x010) == 0x010:
		return 0
	else:
		return 4

def computeZ3S0W1(case):
	if (case & 0xFF8) in (
		0x0E0, 0x0F0, 0x2A0, 0x2B0, 0x8E0, 0x8F0, 0xAA0, 0xAB0, 0xBB0, 0xCF0
		):
		return 8
	elif (case & 0xFF8) in (
		0x0A0, 0x1A0, 0x4A0, 0x8A0,
		0x1F0, 0x4F0, 0x5F0, 0x9F0, 0xDF0,
		0x0B0, 0x1B0, 0x3B0, 0x4B0, 0x5B0, 0x6B0, 0x7B0,
		0x8B0, 0x9B0, 0xCB0, 0xDB0, 0xEB0, 0xFB0
		):
		return 7
	elif (case & 0xFF1) in (0x130, 0x170, 0x330, 0x370, 0x770):
		return 4
	elif (case & 0xFF8) in (
		0x3A0, 0x5A0, 0x7A0, 0x9A0, 0xBA0, 0xCA0, 0xDA0, 0xEA0,
		0x2E0, 0x4E0, 0x5E0, 0x9E0, 0xAE0, 0xCE0,
		0x2F0, 0x3F0, 0x6F0, 0x7F0, 0xAF0, 0xBF0, 0xEF0, 0xFF0
		):
		return 4
	elif (case & 0x0F0) in (0x000, 0x010, 0x040, 0x050, 0x090, 0x0D0):
		return 4
	else:
		return 0

def computeZ3S1W1(case):
	if (case & 0xFF1) in (0x170, 0x130, 0x330, 0x370, 0x770):
		return 12
	elif (case & 0xFF8) in (0x0E0, 0x0F0, 0x8E0, 0x8F0, 0xCF0):
		return 12
	elif (case & 0xFF1) in (0x920, 0x960, 0xB20, 0xB60, 0xBE0):
		return 4
	elif (case & 0xFF8) in (0x2A0, 0x2B0, 0xAA0, 0xAB0, 0xBB0):
		return 4
	elif (case & 0x020) == 0:
		return 4
	elif (case & 0xFF1) in (
		0x120, 0x160, 0x1E0, 0x320, 0x360, 0x3E0,
		0x520, 0x560, 0x570, 0x5E0, 0x760, 0x7E0,
		0x9E0, 0xD60, 0xDE0, 0xDF0, 0xF60, 0xFE0
		):
		return 2
	elif (case & 0xFF8) in (
		0x0A0, 0x0B0, 0x1B0, 0x3B0, 0x4A0, 0x4B0,
		0x4F0, 0x5B0, 0x6B0, 0x7B0, 0x7F0, 0x8A0,
		0x8B0, 0x9B0, 0xCB0, 0xDB0, 0xEB0, 0xFB0
		):
		return 2
	else:
		return 0

def genExpr3():
	quadrant = [
		[ None ] * 4
		for case in xrange(1 << 12)
		]
	quadrantPerm = (0, 2, 1, 3)
	casePerm = computeCasePermutation((0, 3, 6, 1, 4, 7, 2, 5, 8))

	for case in xrange(1 << 12):
		w0 = computeZ3S0W0(case)
		w1 = computeZ3S0W1(case)
		w2 = computeZ3S0W1(permuteCase(case, casePerm))
		weights = (w0, w1, w2, 16 - w0 - w1 - w2)
		quadrant[case][0] = simplifyWeights(weights)

	for case in xrange(1 << 12):
		w1 = computeZ3S1W1(case)
		weights = (0, w1, 0, 16 - w1)
		quadrant[case][1] = simplifyWeights(weights)

	for case in xrange(1 << 12):
		mirrorCase = permuteCase(case, casePerm)
		quadrant[case][2] = permute(quadrant[mirrorCase][1], quadrantPerm)

	for case in xrange(1 << 12):
		quadrant[case][3] = (0, 0, 0, 1)

	return quadrant

def computeZ4S0W0(case):
	if (case & 0xFF8) in (
		0x1A8, 0x4A8,
		0x0A0, 0x1A0, 0x2A0, 0x3A0, 0x4A0, 0x5A0, 0x7A0,
		0x8A0, 0x9A0, 0xAA0, 0xBA0, 0xCA0, 0xDA0, 0xEA0,
		0x0E0, 0x2E0, 0x4E0, 0x5E0, 0x8E0, 0x9E0, 0xAE0, 0xCE0
		):
		return 0
	elif (case & 0x0B0) == 0:
		return 0
	elif (case & 0x010) == 0x010:
		return 0
	else:
		return 6

def computeZ4S0W1(case):
	if (case & 0xFF8) in (
		0x0A0, 0x1A0, 0x2A0, 0x4A0, 0x8A0, 0xAA0,
		0x0E0, 0x8E0,
		0x0F0, 0x1F0, 0x4F0, 0x5F0, 0x8F0, 0x9F0, 0xCF0, 0xDF0
		):
		return 8
	elif (case & 0x0F8) == 0x0B0:
		return 8
	elif (case & 0xFF4) in (
		0x090, 0x190, 0x290, 0x390, 0x590, 0x790,
		0x890, 0x990, 0xB90, 0xC90, 0xE90, 0xA90, 0xD90, 0xF90,
		0x0D0, 0x1D0, 0x2D0, 0x3D0, 0x5D0,
		0x8D0, 0x9D0, 0xAD0, 0xBD0, 0xCD0, 0xDD0, 0xED0, 0xFD0
		):
		return 6
	elif (case & 0x0B4) == 0x094:
		return 6
	elif (case & 0xFF1) in (
		0x130, 0x170, 0x330, 0x370, 0x770
		):
		return 4
	elif (case & 0xFF8) in (
		0x3A0, 0x5A0, 0x7A0, 0x9A0, 0xBA0, 0xCA0, 0xDA0, 0xEA0,
		0x2E0, 0x4E0, 0x5E0, 0x9E0, 0xAE0, 0xCE0,
		0x2F0, 0x3F0, 0x6F0, 0x7F0, 0xAF0, 0xBF0, 0xEF0, 0xFF0
		):
		return 4
	elif (case & 0x0A0) == 0:
		return 4
	else:
		return 0

def computeZ4S1W0(case):
	if (case & 0xFF8) in (
		0x6A0, 0xFA0,
		0x1E0, 0xDE0, 0x6E0, 0xEE0, 0x3E0, 0x7E0, 0xBE0, 0xFE0,
		0x9A8, 0xCA8, 0x0A8, 0x8A8, 0x5A8, 0xDA8,
		0x2A8, 0x3A8, 0x6A8, 0x7A8, 0xAA8, 0xBA8, 0xEA8, 0xFA8
		):
		return 4
	elif (case & 0x0F8) in (0x020, 0x060, 0x028, 0x068, 0x0E8):
		return 4
	elif (case & 0x0B0) == 0x080:
		return 2
	else:
		return 0

def computeZ4S1W1(case):
	if (case & 0xFF1) in (0x130, 0x170, 0x330, 0x370, 0x770):
		return 12
	elif (case & 0xFF8) in (0x0E0, 0x0F0, 0x8E0, 0x8F0, 0xCF0):
		return 10
	elif (case & 0xFF8) in (
		0x0A0, 0x1A0, 0x2A0, 0x4A0, 0x8A0, 0xAA0,
		0x1F0, 0x4F0, 0x5F0, 0x9F0, 0xDF0
		):
		return 8
	elif (case & 0x0F8) == 0x0B0:
		return 8
	elif (case & 0x0B0) == 0x090:
		return 6
	elif (case & 0xFF8) in (
		0x3A0, 0x5A0, 0x7A0, 0x9A0, 0xBA0, 0xCA0, 0xDA0, 0xEA0, 
		0x2E0, 0x4E0, 0x5E0, 0xAE0, 0x9E0, 0xCE0,
		):
		return 4
	elif (case & 0x0B0) in (0x000, 0x010, 0x080):
		return 4
	else:
		return 0

def computeZ4S1W2(case):
	if (case & 0xFF8) in (0x0E0, 0x0F0, 0x8E0, 0x8F0, 0xCF0):
		return 6
	elif (case & 0xFF8) in (0x2A0, 0x2B0, 0xAA0, 0xAB0, 0xBB0):
		return 4
	elif (case & 0xFF1) in (
		0x030, 0x230, 0x430, 0x530, 0x630, 0x730,
		0x830, 0x930, 0xA30, 0xB30, 0xC30, 0xD30, 0xE30, 0xF30,
		0x070, 0x270, 0x470, 0x570, 0x670,
		0x870, 0x970, 0xA70, 0xB70, 0xC70, 0xD70, 0xE70, 0xF70, 
		):
		return 2
	elif (case & 0x0B1) in (0x000, 0x001, 0x010, 0x011, 0x031):
		return 2
	else:
		return 0

def computeZ4S3W0(case):
	if (case & 0xFF8) in (
		0x1A8, 0x4A8,
		0x0A0, 0x1A0, 0x2A0, 0x3A0, 0x4A0, 0x5A0, 0x7A0,
		0x8A0, 0x9A0, 0xAA0, 0xBA0, 0xCA0, 0xDA0, 0xEA0,
		0x0E0, 0x2E0, 0x4E0, 0x5E0, 0x8E0, 0x9E0, 0xAE0, 0xCE0,
		):
		return 0
	elif (case & 0x0B0) == 0:
		return 0
	elif (case & 0x010) == 0x010:
		return 0
	else:
		return 2

def computeZ4S3W1(case):
	if (case & 0xFF8) in (
		0x2A0, 0x2B0, 0xAA0, 
		0xAB0, 0xBB0,
		0x0E0, 0x8E0,
		0x0F0, 0x8F0, 0xCF0
		):
		return 2
	elif (case & 0x0B0) in (0x000, 0x010, 0x090):
		return 2
	else:
		return 0

def genExpr4():
	quadrant = [
		[ None ] * 4
		for case in xrange(1 << 12)
		]
	quadrantPerm = (0, 2, 1, 3)
	casePerm = computeCasePermutation((0, 3, 6, 1, 4, 7, 2, 5, 8))

	for case in xrange(1 << 12):
		w0 = computeZ4S0W0(case)
		w1 = computeZ4S0W1(case)
		w2 = computeZ4S0W1(permuteCase(case, casePerm))
		quadrant[case][0] = simplifyWeights((w0, w1, w2, 16 - w0 - w1 - w2))

	for case in xrange(1 << 12):
		w0 = computeZ4S1W0(case)
		w1 = computeZ4S1W1(case)
		w2 = computeZ4S1W2(case)
		quadrant[case][1] = simplifyWeights((w0, w1, w2, 16 - w0 - w1 - w2))

	for case in xrange(1 << 12):
		mirrorCase = permuteCase(case, casePerm)
		quadrant[case][2] = permute(quadrant[mirrorCase][1], quadrantPerm)

	for case in xrange(1 << 12):
		w0 = computeZ4S3W0(case)
		w1 = computeZ4S3W1(case)
		w2 = computeZ4S3W1(permuteCase(case, casePerm))
		quadrant[case][3] = simplifyWeights((w0, w1, w2, 16 - w0 - w1 - w2))

	return quadrant

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
