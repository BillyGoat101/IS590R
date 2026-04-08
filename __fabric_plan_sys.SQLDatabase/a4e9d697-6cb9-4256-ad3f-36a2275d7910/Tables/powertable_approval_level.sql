CREATE TABLE [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[powertable_approval_level] (
    [id]          INT            IDENTITY (1, 1) NOT NULL,
    [approvalId]  INT            NOT NULL,
    [name]        VARCHAR (255)  NOT NULL,
    [description] VARCHAR (255)  NOT NULL,
    [level]       INT            CONSTRAINT [DF_7772b5b22e1bfd90ef04a407e50] DEFAULT ((1)) NOT NULL,
    [status]      INT            CONSTRAINT [DF_dc5c676949f2b2c3f068851d947] DEFAULT ((10)) NOT NULL,
    [createdBy]   NVARCHAR (128) NOT NULL,
    [updatedBy]   NVARCHAR (128) NOT NULL,
    [createdAt]   INT            NOT NULL,
    [updatedAt]   INT            NOT NULL,
    CONSTRAINT [PK_423a6b7d4fe4163af1d7c56fddb] PRIMARY KEY CLUSTERED ([id] ASC),
    CONSTRAINT [FK_c83f41d1a622e4368ad562c3310] FOREIGN KEY ([approvalId]) REFERENCES [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[powertable_approval] ([id])
);


GO

