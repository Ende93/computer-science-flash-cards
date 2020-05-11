drop table if exists cards;
create table cards (
  id integer primary key autoincrement,
  type tinyint not null, /* 1 for vocab, 2 for code */
  language text,
  front text not null,
  back text not null,
  weight integer default 0,
  timestamp integer default 0,
  known boolean default 0
);
