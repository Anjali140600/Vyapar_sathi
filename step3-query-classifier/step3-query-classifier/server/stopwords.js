/** Common English fillers removed when extracting “related words”. */
module.exports = new Set(
  `a an the and or but if as of at by for from in into like near off on onto out over past per than through to under until up with without
is are was were be been being do does did doing done have has had having
i me my we our you your he she it they them their what which who whom this that these those
there here when where why how all any both each few more most other some such no nor not only same so than too very just can could should would will
about after again against all also am an and another any are as at
before being below between both but by
could did do does doing down during each few for from further had has have having he her here hers herself him himself his how
if in into is it its itself
just like me more most much my myself
no nor not now of off on once only or other ought our ours ourselves out over own
same she should so some such than that the their theirs them themselves then there these they this those through to too
under until up very was we were what when where which while who whom whose why will with would
you your yours yourself yourselves
please tell give show find get list help want need know
something anything everything nothing someone anyone
myself yourself
umm uh er um hey hello hi ok okay yes no`.split(/\s+/)
);
